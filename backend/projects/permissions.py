"""Project-level RBAC helpers on top of workspace roles."""

from projects.models import ProjectMember
from workspaces.models import WorkspaceMember
from workspaces.services import get_membership, has_min_role


ROLE_RANK = {
    ProjectMember.Role.VIEWER: 0,
    ProjectMember.Role.CONTRIBUTOR: 1,
    ProjectMember.Role.MANAGER: 2,
}


def get_project_membership(project, user):
    if project is None or user is None or not user.is_authenticated:
        return None
    return ProjectMember.objects.filter(project=project, user=user).first()


def has_project_min_role(project, user, minimum: str) -> bool:
    """Workspace owners/editors keep access; otherwise use ProjectMember role."""
    if has_min_role(project.workspace, user, WorkspaceMember.Role.OWNER):
        return True
    membership = get_project_membership(project, user)
    if membership is not None:
        return ROLE_RANK.get(membership.role, -1) >= ROLE_RANK.get(minimum, 99)
    # Fall back to workspace role for members without an explicit project role.
    workspace_membership = get_membership(project.workspace, user)
    if workspace_membership is None:
        return False
    if minimum == ProjectMember.Role.VIEWER:
        return True
    if minimum == ProjectMember.Role.CONTRIBUTOR:
        return workspace_membership.role in {
            WorkspaceMember.Role.EDITOR,
            WorkspaceMember.Role.OWNER,
        }
    return workspace_membership.role == WorkspaceMember.Role.OWNER
