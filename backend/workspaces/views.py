from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from notifications.models import Notification
from notifications.signals import create_notification
from workspaces.dashboard import build_workspace_dashboard
from workspaces.invitation_services import accept_invitation, create_workspace_invitation
from workspaces.mixins import IsWorkspaceOwner, WorkspaceMixin
from workspaces.models import WorkspaceInvitation, WorkspaceMember
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


class WorkspaceDashboardView(WorkspaceMixin, APIView):
    def get(self, request):
        workspace = self.get_workspace()
        return Response(build_workspace_dashboard(workspace, request.user))


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
            request.user,
            Notification.NotificationType.INVITE,
            f"Добро пожаловать в «{workspace.name}»",
            link=f"/settings?workspace={workspace.id}",
            workspace=workspace,
        )
        return Response(
            {
                "workspace_id": workspace.id,
                "name": workspace.name,
                "role": membership.role if membership else None,
            }
        )


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
