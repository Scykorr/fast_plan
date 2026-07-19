from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import SAFE_METHODS, BasePermission

from workspaces.models import WorkspaceMember
from workspaces.services import get_membership, get_request_workspace, has_min_role


class WorkspaceMixin:
    """Shared workspace resolution for API views."""

    def get_workspace(self):
        workspace = get_request_workspace(self.request)
        if workspace is None:
            header = self.request.headers.get("X-Workspace-Id")
            if header not in (None, ""):
                raise PermissionDenied("You are not a member of this workspace.")
            raise NotFound("Workspace not found.")
        return workspace

    def get_membership(self):
        return get_membership(self.get_workspace(), self.request.user)

    def require_owner(self, workspace=None, user=None):
        workspace = workspace or self.get_workspace()
        user = user or self.request.user
        membership = get_membership(workspace, user)
        if membership is None or membership.role != WorkspaceMember.Role.OWNER:
            raise PermissionDenied("Only workspace owner can perform this action.")

    def require_editor(self, workspace=None, user=None):
        workspace = workspace or self.get_workspace()
        user = user or self.request.user
        if not has_min_role(workspace, user, WorkspaceMember.Role.EDITOR):
            raise PermissionDenied("Editor role required.")


class IsWorkspaceMember(BasePermission):
    """Require membership in the resolved workspace."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        workspace = get_request_workspace(request)
        if workspace is None:
            # Let the view raise NotFound/PermissionDenied with a clear message.
            return True
        return get_membership(workspace, request.user) is not None


class IsWorkspaceEditorOrReadOnly(BasePermission):
    """Viewers can read; editors and owners can write."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        workspace = get_request_workspace(request)
        if workspace is None:
            return True
        if request.method in SAFE_METHODS:
            return get_membership(workspace, request.user) is not None
        return has_min_role(workspace, request.user, WorkspaceMember.Role.EDITOR)


class IsWorkspaceOwner(BasePermission):
    """Owner-only mutations; members can still GET if mixed on same view."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        workspace = get_request_workspace(request)
        if workspace is None:
            return True
        if request.method in SAFE_METHODS:
            return get_membership(workspace, request.user) is not None
        return has_min_role(workspace, request.user, WorkspaceMember.Role.OWNER)
