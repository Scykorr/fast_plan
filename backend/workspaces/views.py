from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from notifications.models import Notification
from notifications.services import create_notification
from workspaces.dashboard import build_workspace_dashboard
from workspaces.invitation_services import (
    accept_invitation,
    create_workspace_invitation,
    resend_workspace_invitation,
)
from workspaces.mixins import IsWorkspaceEditorOrReadOnly, IsWorkspaceOwner, WorkspaceMixin
from workspaces.models import MemberCapacity, WorkspaceInvitation, WorkspaceMember
from workspaces.search import build_capacity_report, list_my_tasks, search_workspace
from workspaces.serializers import (
    WorkspaceInvitationSerializer,
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


class WorkspaceDashboardView(WorkspaceMixin, APIView):
    def get(self, request):
        workspace = self.get_workspace()
        return Response(build_workspace_dashboard(workspace, request.user))


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
        member.role = role
        member.save(update_fields=["role"])
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
        member.delete()
        from workspaces.services import clear_invalid_active_workspace

        clear_invalid_active_workspace(member.user)
        return Response(status=status.HTTP_204_NO_CONTENT)
