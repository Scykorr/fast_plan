from workspaces.models import Workspace, WorkspaceMember

WORKSPACE_HEADER = "HTTP_X_WORKSPACE_ID"

ROLE_RANK = {
    WorkspaceMember.Role.VIEWER: 0,
    WorkspaceMember.Role.EDITOR: 1,
    WorkspaceMember.Role.OWNER: 2,
}


def get_user_workspaces(user):
    return Workspace.objects.filter(memberships__user=user).distinct().order_by("created_at")


def get_membership(workspace, user):
    if workspace is None or user is None or not user.is_authenticated:
        return None
    return WorkspaceMember.objects.filter(workspace=workspace, user=user).first()


def has_min_role(workspace, user, minimum: str) -> bool:
    membership = get_membership(workspace, user)
    if membership is None:
        return False
    return ROLE_RANK.get(membership.role, -1) >= ROLE_RANK.get(minimum, 99)


def get_oldest_workspace(user):
    return get_user_workspaces(user).first()


def get_user_workspace(user):
    """Backward-compatible preference/oldest resolution (no request header)."""
    active_id = getattr(user, "active_workspace_id", None)
    if active_id:
        workspace = get_user_workspaces(user).filter(pk=active_id).first()
        if workspace is not None:
            return workspace
    return get_oldest_workspace(user)


def resolve_workspace_for_user(user, workspace_id: int | None):
    if workspace_id is None:
        return get_user_workspace(user)
    workspace = get_user_workspaces(user).filter(pk=workspace_id).first()
    return workspace


def get_request_workspace(request):
    """
    Resolve active workspace for a request:
    1. X-Workspace-Id header (must be a membership)
    2. user.active_workspace preference
    3. oldest membership
    """
    auth = getattr(request, "auth", None)
    token_workspace = getattr(auth, "workspace", None)
    if token_workspace is not None:
        return token_workspace

    header_value = request.META.get(WORKSPACE_HEADER) or request.headers.get(
        "X-Workspace-Id"
    )
    if header_value not in (None, ""):
        try:
            workspace_id = int(header_value)
        except (TypeError, ValueError):
            return None
        return resolve_workspace_for_user(request.user, workspace_id)

    return get_user_workspace(request.user)


def set_active_workspace(user, workspace) -> None:
    if user.active_workspace_id == workspace.id:
        return
    user.active_workspace = workspace
    user.save(update_fields=["active_workspace"])


def clear_invalid_active_workspace(user) -> None:
    active_id = getattr(user, "active_workspace_id", None)
    if not active_id:
        return
    if not WorkspaceMember.objects.filter(workspace_id=active_id, user=user).exists():
        user.active_workspace = get_oldest_workspace(user)
        user.save(update_fields=["active_workspace"])
