from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from notifications.models import Notification
from notifications.signals import create_notification
from workspaces.invitation_services import accept_invitation, create_workspace_invitation
from workspaces.models import Workspace, WorkspaceInvitation, WorkspaceMember
from workspaces.serializers import (
    WorkspaceInvitationSerializer,
    WorkspaceMemberSerializer,
)
from workspaces.services import get_user_workspace


class WorkspaceMixin:
    def get_workspace(self):
        workspace = get_user_workspace(self.request.user)
        if workspace is None:
            raise NotFound("Workspace not found.")
        return workspace

    def require_owner(self, workspace, user):
        membership = WorkspaceMember.objects.filter(workspace=workspace, user=user).first()
        if membership is None or membership.role != WorkspaceMember.Role.OWNER:
            raise PermissionDenied("Only workspace owner can perform this action.")


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
        create_notification(
            request.user,
            Notification.NotificationType.INVITE,
            f"Добро пожаловать в «{workspace.name}»",
            link="/settings",
        )
        return Response({"workspace_id": workspace.id, "name": workspace.name})


class WorkspaceMemberDetailView(WorkspaceMixin, APIView):
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
        return Response(status=status.HTTP_204_NO_CONTENT)
