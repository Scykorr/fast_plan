"""ACL helpers for project, workspace, and DM chat rooms."""

from django.db.models import Q

from projects.models import Project, ProjectMember
from projects.permissions import get_project_membership, has_project_min_role
from workspaces.models import Workspace, WorkspaceMember
from workspaces.services import get_membership, has_min_role

from chats.models import ChatRoom, ChatRoomMute


def get_or_create_project_room(project: Project) -> ChatRoom:
    room, _ = ChatRoom.objects.get_or_create(
        project=project,
        defaults={"scope": ChatRoom.Scope.PROJECT},
    )
    return room


def get_or_create_workspace_room(workspace: Workspace) -> ChatRoom:
    room, _ = ChatRoom.objects.get_or_create(
        scope=ChatRoom.Scope.WORKSPACE,
        workspace=workspace,
        defaults={},
    )
    return room


def get_or_create_dm_room(workspace: Workspace, user_a, user_b) -> ChatRoom:
    if user_a.id == user_b.id:
        raise ValueError("Cannot create DM with yourself.")
    low, high = (user_a, user_b) if user_a.id < user_b.id else (user_b, user_a)
    room, _ = ChatRoom.objects.get_or_create(
        scope=ChatRoom.Scope.DM,
        workspace=workspace,
        dm_user_low=low,
        dm_user_high=high,
        defaults={},
    )
    return room


def can_access(room: ChatRoom, user) -> bool:
    if user is None or not user.is_authenticated:
        return False
    if room.scope == ChatRoom.Scope.PROJECT:
        return has_project_min_role(room.project, user, ProjectMember.Role.VIEWER)
    if room.scope == ChatRoom.Scope.DM:
        return user.id in {room.dm_user_low_id, room.dm_user_high_id}
    return get_membership(room.workspace, user) is not None


def is_moderator(room: ChatRoom, user) -> bool:
    if user is None or not user.is_authenticated:
        return False
    if room.scope == ChatRoom.Scope.DM:
        return can_access(room, user)
    if room.scope == ChatRoom.Scope.PROJECT:
        project = room.project
        if has_min_role(project.workspace, user, WorkspaceMember.Role.OWNER):
            return True
        if project.manager_id == user.id:
            return True
        membership = get_project_membership(project, user)
        return bool(membership and membership.role == ProjectMember.Role.MANAGER)
    return has_min_role(room.workspace, user, WorkspaceMember.Role.OWNER)


def is_muted(room: ChatRoom, user) -> bool:
    if user is None or not user.is_authenticated:
        return False
    return ChatRoomMute.objects.filter(room=room, user=user).exists()


def can_post(room: ChatRoom, user) -> bool:
    if room.is_archived or room.status == ChatRoom.Status.ARCHIVED:
        return False
    if not can_access(room, user):
        return False
    if room.status == ChatRoom.Status.DISABLED:
        return False
    if is_moderator(room, user) and room.scope != ChatRoom.Scope.DM:
        return True
    if room.scope == ChatRoom.Scope.DM:
        return not is_muted(room, user)
    if room.status == ChatRoom.Status.ANNOUNCEMENTS:
        return False
    if is_muted(room, user):
        return False
    return True


def can_edit_message(room: ChatRoom, message, user) -> bool:
    if message.is_deleted:
        return False
    if not can_access(room, user):
        return False
    if is_moderator(room, user) and room.scope != ChatRoom.Scope.DM:
        return True
    return message.author_id == user.id and can_post(room, user)


def can_delete_message(room: ChatRoom, message, user) -> bool:
    if message.is_deleted:
        return False
    if not can_access(room, user):
        return False
    if is_moderator(room, user):
        return True
    return message.author_id == user.id


def can_forward_into(room: ChatRoom, user) -> bool:
    return can_post(room, user)


def list_accessible_rooms(user, *, include_archived: bool = False):
    """Rooms the user can access (for forward target picker / DM list)."""
    from projects.models import Project

    workspace_ids = list(
        WorkspaceMember.objects.filter(user=user).values_list("workspace_id", flat=True)
    )
    rooms = []
    for workspace_id in workspace_ids:
        try:
            workspace = Workspace.objects.get(pk=workspace_id)
        except Workspace.DoesNotExist:
            continue
        room = get_or_create_workspace_room(workspace)
        if can_access(room, user):
            rooms.append(room)

    project_ids = set(
        ProjectMember.objects.filter(user=user).values_list("project_id", flat=True)
    )
    project_ids.update(
        Project.objects.filter(workspace_id__in=workspace_ids).values_list("id", flat=True)
    )
    for project in Project.objects.filter(id__in=project_ids).select_related("workspace"):
        if not has_project_min_role(project, user, ProjectMember.Role.VIEWER):
            continue
        room = get_or_create_project_room(project)
        if can_access(room, user):
            rooms.append(room)

    dm_rooms = ChatRoom.objects.filter(scope=ChatRoom.Scope.DM).filter(
        Q(dm_user_low=user) | Q(dm_user_high=user)
    ).select_related("workspace", "dm_user_low", "dm_user_high")
    rooms.extend(list(dm_rooms))

    seen = set()
    unique = []
    for room in rooms:
        if room.id in seen:
            continue
        if not include_archived and room.is_archived:
            continue
        seen.add(room.id)
        unique.append(room)
    return unique


def recipient_users(room: ChatRoom):
    """Users who should receive chat notifications for this room."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    if room.scope == ChatRoom.Scope.DM:
        return list(
            User.objects.filter(id__in=[room.dm_user_low_id, room.dm_user_high_id])
        )
    if room.scope == ChatRoom.Scope.PROJECT:
        project = room.project
        user_ids = set(
            ProjectMember.objects.filter(project=project).values_list("user_id", flat=True)
        )
        user_ids.update(
            WorkspaceMember.objects.filter(workspace=project.workspace).values_list(
                "user_id", flat=True
            )
        )
        if project.manager_id:
            user_ids.add(project.manager_id)
        return list(User.objects.filter(id__in=user_ids))
    return list(
        User.objects.filter(
            id__in=WorkspaceMember.objects.filter(workspace=room.workspace).values_list(
                "user_id", flat=True
            )
        )
    )


def archive_disabled_rooms(*, older_than_days: int = 30) -> int:
    """Mark disabled rooms as archived when disabled long enough. Returns count."""
    from datetime import timedelta

    from django.utils import timezone

    cutoff = timezone.now() - timedelta(days=older_than_days)
    qs = ChatRoom.objects.filter(
        status=ChatRoom.Status.DISABLED,
        archived_at__isnull=True,
        status_changed_at__lte=cutoff,
    )
    count = 0
    now = timezone.now()
    for room in qs.iterator():
        room.status = ChatRoom.Status.ARCHIVED
        room.archived_at = now
        room.save(update_fields=["status", "archived_at"])
        count += 1
    return count
