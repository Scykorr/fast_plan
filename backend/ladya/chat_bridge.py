"""Internal Fast Plan chat ↔ Ladya (no Telegram)."""

from __future__ import annotations

from django.utils import timezone

from chats.models import ChatMessage, ChatRoom
from chats.services import get_or_create_workspace_room
from ladya.models import IntakeRequest, Laboratory, Package
from notifications.models import Notification
from notifications.services import create_notification
from workspaces.models import WorkspaceMember


def notify_intake_editors(workspace, intake: IntakeRequest) -> None:
    members = WorkspaceMember.objects.filter(
        workspace=workspace,
        role__in=[WorkspaceMember.Role.OWNER, WorkspaceMember.Role.EDITOR],
    ).select_related("user")
    title = "Ladya: новое обращение"
    message = (intake.body or "")[:240]
    link = "/ladya/intake"
    for membership in members:
        create_notification(
            user=membership.user,
            workspace=workspace,
            notification_type=Notification.NotificationType.CHAT,
            title=title,
            message=message,
            link=link,
            dedupe_key=f"ladya-intake-{intake.id}-user-{membership.user_id}",
        )


def ensure_laboratory_chat_room(lab: Laboratory) -> ChatRoom:
    """Bind lab to the workspace portfolio chat (one room per workspace)."""
    room = get_or_create_workspace_room(lab.workspace)
    if lab.chat_room_id != room.id:
        lab.chat_room = room
        lab.updated_at = timezone.now()
        lab.save(update_fields=["chat_room", "updated_at"])
    return room


def room_allows_intake_create(workspace, room: ChatRoom) -> bool:
    """True if room is linked to central_lad or external_intake in this workspace."""
    return Laboratory.objects.filter(
        workspace=workspace,
        chat_room=room,
        is_active=True,
        kind__in=[Laboratory.Kind.CENTRAL_LAD, Laboratory.Kind.EXTERNAL_INTAKE],
    ).exists()


def create_intake_from_chat_message(
    *, workspace, message: ChatMessage, actor
) -> IntakeRequest:
    room = message.room
    if room.host_workspace_id != workspace.id:
        raise ValueError("Сообщение из другого workspace.")
    if not room_allows_intake_create(workspace, room):
        raise ValueError(
            "Комната не привязана к central_lad / external_intake. "
            "Сначала «Создать комнату» на карточке лаборатории входа."
        )
    if message.is_deleted:
        raise ValueError("Сообщение удалено.")
    body = (message.body or "").strip()
    if message.is_encrypted:
        raise ValueError("Из E2E-сообщения Intake не создаём — нужен открытый текст.")
    if not body:
        raise ValueError("В сообщении нет текста.")
    author = message.author
    contact = ""
    if author is not None:
        contact = (getattr(author, "email", None) or str(author.pk))[:255]
    intake = IntakeRequest.objects.create(
        workspace=workspace,
        body=body[:8000],
        contact=contact,
        status=IntakeRequest.Status.NEW,
        source=IntakeRequest.Source.INTERNAL_CHAT,
        created_by=actor,
    )
    notify_intake_editors(workspace, intake)
    return intake


def post_package_notice(
    *, package: Package, actor, text: str | None = None
) -> ChatMessage:
    lab = package.to_laboratory
    if lab is None or lab.chat_room_id is None:
        raise ValueError("У лаборатории-получателя нет привязанного чата.")
    room = lab.chat_room
    if room.host_workspace_id != package.workspace_id:
        raise ValueError("Чат лаборатории из другого workspace.")
    body = (text or "").strip()
    if not body:
        body = (
            f"Пакет {package.display_code}: {package.title}\n"
            f"/ladya/packages/{package.id}"
        )
    return ChatMessage.objects.create(
        room=room,
        author=actor,
        body=body[:8000],
    )
