import secrets
from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.services import log_audit
from notifications.models import Notification
from notifications.services import create_notification
from workspaces.dashboard import build_workspace_dashboard
from workspaces.events import event_stream, subscribe, unsubscribe
from workspaces.invitation_services import (
    accept_invitation,
    create_workspace_invitation,
    resend_workspace_invitation,
)
from workspaces.mixins import IsWorkspaceEditorOrReadOnly, IsWorkspaceOwner, WorkspaceMixin
from workspaces.models import (
    ExchangeRate,
    MemberCapacity,
    WebhookDelivery,
    WebhookEndpoint,
    WorkspaceAPIToken,
    WorkspaceInvitation,
    WorkspaceMember,
)
from workspaces.search import build_capacity_report, list_my_tasks, search_workspace
from workspaces.serializers import (
    WorkspaceInvitationSerializer,
    WebhookDeliverySerializer,
    WebhookEndpointSerializer,
    WorkspaceAPITokenCreateSerializer,
    WorkspaceAPITokenSerializer,
    WorkspaceMemberSerializer,
    WorkspaceSummarySerializer,
)
from workspaces.services import (
    get_membership,
    get_request_workspace,
    get_user_workspaces,
    set_active_workspace,
)
from django.contrib.auth import get_user_model
from datetime import date
from django.utils import timezone


class WorkspaceDashboardView(WorkspaceMixin, APIView):
    def get(self, request):
        workspace = self.get_workspace()
        return Response(build_workspace_dashboard(workspace, request.user))


class WorkspaceEventsView(WorkspaceMixin, APIView):
    """SSE stream of realtime workspace events (Kanban moves, WBS edits, comments).

    In-process pub/sub only (see ``workspaces.events`` docstring) — works for
    a single Django process; use cookie auth so ``EventSource`` (which can't
    set custom headers) authenticates the same way as regular GET requests.
    """

    def get(self, request):
        workspace = self.get_workspace()
        q = subscribe(workspace.id)

        def stream():
            try:
                yield from event_stream(workspace.id, q)
            finally:
                unsubscribe(workspace.id, q)

        response = StreamingHttpResponse(stream(), content_type="text/event-stream")
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response


class WorkspaceSearchView(WorkspaceMixin, APIView):
    def get(self, request):
        workspace = self.get_workspace()
        query = request.query_params.get("q", "")
        types = request.query_params.get("types")
        type_list = (
            [item.strip() for item in types.split(",") if item.strip()]
            if types
            else None
        )
        limit = min(int(request.query_params.get("limit", 20)), 50)
        return Response(
            search_workspace(workspace, query, types=type_list, limit=limit)
        )


class WorkspaceMyTasksView(WorkspaceMixin, APIView):
    def get(self, request):
        workspace = self.get_workspace()
        User = get_user_model()
        assignee_param = request.query_params.get("assignee")
        if assignee_param:
            assignee = get_object_or_404(
                User.objects.filter(workspace_memberships__workspace=workspace),
                pk=int(assignee_param),
            )
        else:
            assignee = request.user
        include_done = request.query_params.get("include_done", "false").lower() == "true"
        overdue_only = request.query_params.get("overdue_only", "false").lower() == "true"
        limit = min(int(request.query_params.get("limit", 50)), 100)
        return Response(
            list_my_tasks(
                workspace,
                assignee,
                include_done=include_done,
                overdue_only=overdue_only,
                limit=limit,
            )
        )


class WorkspaceCapacityView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get(self, request):
        workspace = self.get_workspace()
        week_start_raw = request.query_params.get("week_start")
        week_start = date.fromisoformat(week_start_raw) if week_start_raw else None
        return Response(build_capacity_report(workspace, week_start=week_start))

    def patch(self, request):
        workspace = self.get_workspace()
        self.require_owner(workspace, request.user)
        user_id = request.data.get("user_id")
        hours = request.data.get("hours_per_week")
        if user_id is None or hours is None:
            raise ValidationError({"detail": "user_id and hours_per_week are required."})
        User = get_user_model()
        user = get_object_or_404(
            User.objects.filter(workspace_memberships__workspace=workspace),
            pk=int(user_id),
        )
        capacity, _ = MemberCapacity.objects.update_or_create(
            workspace=workspace,
            user=user,
            defaults={"hours_per_week": int(hours)},
        )
        return Response(
            {
                "user_id": capacity.user_id,
                "hours_per_week": capacity.hours_per_week,
            }
        )


def _require_session_owner(view, request, workspace):
    if isinstance(getattr(request, "auth", None), WorkspaceAPIToken):
        raise PermissionDenied("Manage integrations with an interactive session.")
    view.require_owner(workspace, request.user)


class WorkspaceAPITokenListCreateView(WorkspaceMixin, APIView):
    def get(self, request):
        workspace = self.get_workspace()
        _require_session_owner(self, request, workspace)
        return Response(
            WorkspaceAPITokenSerializer(workspace.api_tokens.all(), many=True).data
        )

    def post(self, request):
        workspace = self.get_workspace()
        _require_session_owner(self, request, workspace)
        serializer = WorkspaceAPITokenCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        expires_at = serializer.validated_data.get("expires_at")
        if expires_at is not None and expires_at <= timezone.now():
            raise ValidationError({"expires_at": "Expiration must be in the future."})
        token, raw_token = WorkspaceAPIToken.issue(
            workspace=workspace,
            name=serializer.validated_data["name"],
            scopes=serializer.validated_data["scopes"],
            created_by=request.user,
            expires_at=expires_at,
        )
        data = WorkspaceAPITokenSerializer(token).data
        data["token"] = raw_token
        log_audit(
            workspace,
            request.user,
            "api_token.create",
            "WorkspaceAPIToken",
            token.id,
            summary=f"Created API token: {token.name}",
            changes={"scopes": token.scopes},
        )
        return Response(data, status=status.HTTP_201_CREATED)


class WorkspaceAPITokenDetailView(WorkspaceMixin, APIView):
    def delete(self, request, token_id):
        workspace = self.get_workspace()
        _require_session_owner(self, request, workspace)
        token = get_object_or_404(workspace.api_tokens, pk=token_id)
        token.revoked_at = timezone.now()
        token.save(update_fields=["revoked_at"])
        log_audit(
            workspace,
            request.user,
            "api_token.revoke",
            "WorkspaceAPIToken",
            token.id,
            summary=f"Revoked API token: {token.name}",
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class WorkspaceWebhookListCreateView(WorkspaceMixin, APIView):
    def get(self, request):
        workspace = self.get_workspace()
        _require_session_owner(self, request, workspace)
        return Response(
            WebhookEndpointSerializer(workspace.webhook_endpoints.all(), many=True).data
        )

    def post(self, request):
        workspace = self.get_workspace()
        _require_session_owner(self, request, workspace)
        serializer = WebhookEndpointSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        secret = secrets.token_urlsafe(32)
        endpoint = serializer.save(
            workspace=workspace,
            created_by=request.user,
            secret=secret,
        )
        data = WebhookEndpointSerializer(endpoint).data
        data["secret"] = secret
        log_audit(
            workspace,
            request.user,
            "webhook.create",
            "WebhookEndpoint",
            endpoint.id,
            summary=f"Created webhook: {endpoint.name}",
            changes={"url": endpoint.url, "events": endpoint.events},
        )
        return Response(data, status=status.HTTP_201_CREATED)


class WorkspaceWebhookDetailView(WorkspaceMixin, APIView):
    def _get_endpoint(self, workspace, endpoint_id):
        return get_object_or_404(workspace.webhook_endpoints, pk=endpoint_id)

    def patch(self, request, endpoint_id):
        workspace = self.get_workspace()
        _require_session_owner(self, request, workspace)
        endpoint = self._get_endpoint(workspace, endpoint_id)
        serializer = WebhookEndpointSerializer(
            endpoint,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, endpoint_id):
        workspace = self.get_workspace()
        _require_session_owner(self, request, workspace)
        endpoint = self._get_endpoint(workspace, endpoint_id)
        endpoint.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class WorkspaceWebhookDeliveryListView(WorkspaceMixin, APIView):
    def get(self, request, endpoint_id):
        workspace = self.get_workspace()
        _require_session_owner(self, request, workspace)
        endpoint = get_object_or_404(workspace.webhook_endpoints, pk=endpoint_id)
        deliveries = WebhookDelivery.objects.filter(endpoint=endpoint)[:50]
        return Response(WebhookDeliverySerializer(deliveries, many=True).data)


class WorkspaceListView(APIView):
    def get(self, request):
        workspaces = get_user_workspaces(request.user)
        active = get_request_workspace(request)
        active_id = active.id if active else None
        memberships = {
            m.workspace_id: m.role
            for m in WorkspaceMember.objects.filter(user=request.user)
        }
        data = [
            {
                "id": workspace.id,
                "name": workspace.name,
                "role": memberships.get(workspace.id, WorkspaceMember.Role.VIEWER),
                "is_active": workspace.id == active_id,
            }
            for workspace in workspaces
        ]
        return Response(WorkspaceSummarySerializer(data, many=True).data)


class WorkspaceActivateView(APIView):
    def post(self, request, workspace_id):
        membership = WorkspaceMember.objects.filter(
            workspace_id=workspace_id,
            user=request.user,
        ).select_related("workspace").first()
        if membership is None:
            raise PermissionDenied("You are not a member of this workspace.")
        set_active_workspace(request.user, membership.workspace)
        return Response(
            {
                "id": membership.workspace.id,
                "name": membership.workspace.name,
                "role": membership.role,
                "is_active": True,
            }
        )


class WorkspaceMemberListView(WorkspaceMixin, APIView):
    def get(self, request):
        workspace = self.get_workspace()
        members = WorkspaceMember.objects.filter(workspace=workspace).select_related("user")
        data = [
            {
                "id": member.id,
                "user_id": member.user_id,
                "email": member.user.email,
                "username": member.user.username,
                "role": member.role,
                "joined_at": member.joined_at,
            }
            for member in members
        ]
        return Response(data)


class WorkspaceInvitationListCreateView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceOwner]

    def get(self, request):
        workspace = self.get_workspace()
        invitations = WorkspaceInvitation.objects.filter(
            workspace=workspace,
            accepted_at__isnull=True,
        )
        return Response(WorkspaceInvitationSerializer(invitations, many=True).data)

    def post(self, request):
        workspace = self.get_workspace()
        self.require_owner(workspace, request.user)
        email = request.data.get("email", "").strip().lower()
        role = request.data.get("role", WorkspaceMember.Role.EDITOR)
        if role not in WorkspaceMember.Role.values:
            raise ValidationError({"role": "Invalid role."})
        if not email:
            raise ValidationError({"email": "Email is required."})
        if WorkspaceMember.objects.filter(workspace=workspace, user__email__iexact=email).exists():
            raise ValidationError({"email": "User is already a member."})
        invitation = create_workspace_invitation(workspace, email, role, request.user)
        log_audit(
            workspace,
            request.user,
            "invitation.create",
            "WorkspaceInvitation",
            invitation.id,
            summary=f"Invited {invitation.email} as {invitation.role}",
            changes={"email": invitation.email, "role": invitation.role},
        )
        return Response(
            WorkspaceInvitationSerializer(invitation).data,
            status=status.HTTP_201_CREATED,
        )


class WorkspaceInvitationAcceptView(APIView):
    def post(self, request, token):
        try:
            workspace = accept_invitation(token, request.user)
        except WorkspaceInvitation.DoesNotExist:
            raise NotFound("Invitation not found.")
        except ValueError as exc:
            raise ValidationError(str(exc))
        membership = get_membership(workspace, request.user)
        create_notification(
            user=request.user,
            notification_type=Notification.NotificationType.INVITE,
            title=f"Добро пожаловать в «{workspace.name}»",
            link=f"/settings?workspace={workspace.id}",
            workspace=workspace,
            dedupe_key=f"invite-accept:{workspace.id}:{request.user.id}",
        )
        return Response(
            {
                "workspace_id": workspace.id,
                "name": workspace.name,
                "role": membership.role if membership else None,
            }
        )


class WorkspaceInvitationDetailView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceOwner]

    def get_pending(self, invitation_id):
        workspace = self.get_workspace()
        self.require_owner(workspace, self.request.user)
        return get_object_or_404(
            WorkspaceInvitation.objects.filter(
                workspace=workspace,
                accepted_at__isnull=True,
            ),
            pk=invitation_id,
        )

    def delete(self, request, invitation_id):
        invitation = self.get_pending(invitation_id)
        workspace = self.get_workspace()
        log_audit(
            workspace,
            request.user,
            "invitation.revoke",
            "WorkspaceInvitation",
            invitation.id,
            summary=f"Revoked invitation for {invitation.email}",
            changes={"email": invitation.email, "role": invitation.role},
        )
        invitation.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def post(self, request, invitation_id):
        """Resend invitation email (also used via .../resend/ route)."""
        invitation = self.get_pending(invitation_id)
        updated = resend_workspace_invitation(invitation)
        return Response(WorkspaceInvitationSerializer(updated).data)


class WorkspaceMemberDetailView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceOwner]

    def patch(self, request, member_id):
        workspace = self.get_workspace()
        self.require_owner(workspace, request.user)
        member = get_object_or_404(
            WorkspaceMember.objects.filter(workspace=workspace),
            pk=member_id,
        )
        role = request.data.get("role")
        if role not in WorkspaceMember.Role.values:
            raise ValidationError({"role": "Invalid role."})
        old_role = member.role
        member.role = role
        member.save(update_fields=["role"])
        log_audit(
            workspace,
            request.user,
            "member.role_change",
            "WorkspaceMember",
            member.id,
            summary=f"Changed {member.user.email} role: {old_role} → {role}",
            changes={"old_role": old_role, "new_role": role, "user_id": member.user_id},
        )
        return Response(WorkspaceMemberSerializer(member).data)

    def delete(self, request, member_id):
        workspace = self.get_workspace()
        self.require_owner(workspace, request.user)
        member = get_object_or_404(
            WorkspaceMember.objects.filter(workspace=workspace),
            pk=member_id,
        )
        if member.user_id == workspace.owner_id:
            raise ValidationError("Cannot remove workspace owner.")
        log_audit(
            workspace,
            request.user,
            "member.remove",
            "WorkspaceMember",
            member.id,
            summary=f"Removed {member.user.email} from workspace",
            changes={"user_id": member.user_id, "role": member.role},
        )
        member.delete()
        from workspaces.services import clear_invalid_active_workspace

        clear_invalid_active_workspace(member.user)
        return Response(status=status.HTTP_204_NO_CONTENT)
