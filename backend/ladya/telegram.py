"""Telegram → IntakeRequest (no DeliveryTask / no agent claim)."""

from __future__ import annotations

import secrets

from django.utils import timezone

from ladya.models import IntakeRequest, LadyaSettings
from notifications.models import Notification
from notifications.services import create_notification
from workspaces.models import WorkspaceMember


def new_telegram_webhook_secret() -> str:
    return secrets.token_urlsafe(24)


def ingest_telegram_intake(settings_row: LadyaSettings, update: dict) -> IntakeRequest | None:
    """Create IntakeRequest from a Telegram Bot API update. Never touches DeliveryTask."""
    if not settings_row.ladya_hub_enabled:
        return None
    message = update.get("message") or update.get("edited_message") or {}
    text = (message.get("text") or message.get("caption") or "").strip()
    if not text:
        return None
    chat = message.get("chat") or {}
    from_user = message.get("from") or {}
    username = (from_user.get("username") or "").strip()
    chat_id = chat.get("id")
    contact_parts = []
    if username:
        contact_parts.append(f"@{username}")
    if chat_id is not None:
        contact_parts.append(f"chat:{chat_id}")
    contact = " ".join(contact_parts)[:255]

    intake = IntakeRequest.objects.create(
        workspace=settings_row.workspace,
        body=text[:8000],
        contact=contact,
        status=IntakeRequest.Status.NEW,
        source=IntakeRequest.Source.TELEGRAM,
        created_by=None,
    )
    _notify_editors(settings_row.workspace, intake)
    return intake


def _notify_editors(workspace, intake: IntakeRequest) -> None:
    members = WorkspaceMember.objects.filter(
        workspace=workspace,
        role__in=[WorkspaceMember.Role.OWNER, WorkspaceMember.Role.EDITOR],
    ).select_related("user")
    title = "Ladya: новое обращение из Telegram"
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


def rotate_telegram_secret(settings_row: LadyaSettings) -> str:
    secret = new_telegram_webhook_secret()
    settings_row.telegram_webhook_secret = secret
    settings_row.updated_at = timezone.now()
    settings_row.save(update_fields=["telegram_webhook_secret", "updated_at"])
    return secret
