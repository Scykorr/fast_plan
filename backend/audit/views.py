from rest_framework.generics import ListAPIView
from rest_framework.permissions import BasePermission

from audit.models import AuditLogEntry
from audit.serializers import AuditLogEntrySerializer
from workspaces.mixins import WorkspaceMixin
from workspaces.models import WorkspaceMember
from workspaces.services import get_request_workspace, has_min_role


class IsWorkspaceEditorOrOwner(BasePermission):
    """Only editors/owners may read the audit log (viewers are excluded)."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        workspace = get_request_workspace(request)
        if workspace is None:
            return True
        return has_min_role(workspace, request.user, WorkspaceMember.Role.EDITOR)


class AuditLogListView(WorkspaceMixin, ListAPIView):
    permission_classes = [IsWorkspaceEditorOrOwner]
    serializer_class = AuditLogEntrySerializer

    def get_queryset(self):
        return AuditLogEntry.objects.filter(
            workspace=self.get_workspace()
        ).select_related("actor")
