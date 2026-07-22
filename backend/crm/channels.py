"""Inbound omnichannel: IMAP email + Telegram → CRM Activity timeline."""

from __future__ import annotations

import email
import email.header
import email.utils
import imaplib
import json
import logging
import urllib.request
from datetime import datetime, timezone as dt_timezone
from email.message import Message

from django.db import IntegrityError
from django.utils import timezone

from crm.models import Activity, ChannelConnection, Person

logger = logging.getLogger("fast_plan")


def _decode_header(raw: str | None) -> str:
    if not raw:
        return ""
    parts = email.header.decode_header(raw)
    out = []
    for chunk, enc in parts:
        if isinstance(chunk, bytes):
            out.append(chunk.decode(enc or "utf-8", errors="replace"))
        else:
            out.append(chunk)
    return "".join(out).strip()


def _message_body(msg: Message) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype == "text/plain" and "attachment" not in str(part.get("Content-Disposition", "")):
                payload = part.get_payload(decode=True) or b""
                charset = part.get_content_charset() or "utf-8"
                return payload.decode(charset, errors="replace")
        return ""
    payload = msg.get_payload(decode=True) or b""
    charset = msg.get_content_charset() or "utf-8"
    return payload.decode(charset, errors="replace")


def _find_person_by_email(workspace, address: str) -> Person | None:
    addr = (address or "").strip().lower()
    if not addr:
        return None
    return Person.objects.filter(workspace=workspace, email__iexact=addr).first()


def _find_person_by_telegram(workspace, username_or_id: str) -> Person | None:
    raw = (username_or_id or "").strip().lstrip("@")
    if not raw:
        return None
    person = Person.objects.filter(workspace=workspace, telegram__iexact=raw).first()
    if person:
        return person
    return Person.objects.filter(workspace=workspace, telegram__iexact=f"@{raw}").first()


def ingest_activity(
    workspace,
    *,
    kind: str,
    channel: str,
    direction: str,
    external_id: str,
    subject: str,
    body: str,
    occurred_at,
    person=None,
    organization=None,
) -> Activity | None:
    if not external_id:
        return None
    if Activity.objects.filter(
        workspace=workspace, channel=channel, external_id=external_id
    ).exists():
        return None
    try:
        return Activity.objects.create(
            workspace=workspace,
            kind=kind,
            channel=channel,
            direction=direction,
            external_id=external_id,
            subject=subject[:255] or "(без темы)",
            body=body or "",
            occurred_at=occurred_at or timezone.now(),
            person=person,
            organization=organization
            or (
                person.organization_memberships.select_related("organization")
                .order_by("-is_primary", "id")
                .first()
                .organization
                if person and person.organization_memberships.exists()
                else None
            ),
        )
    except IntegrityError:
        return None


def sync_imap_connection(connection: ChannelConnection) -> dict:
    cfg = connection.config or {}
    host = (cfg.get("host") or "").strip()
    username = (cfg.get("username") or "").strip()
    password = cfg.get("password") or ""
    port = int(cfg.get("port") or 993)
    use_ssl = bool(cfg.get("use_ssl", True))
    folder = (cfg.get("folder") or "INBOX").strip() or "INBOX"
    limit = min(50, max(1, int(cfg.get("limit") or 20)))

    if not host or not username:
        raise ValueError("IMAP host and username are required.")

    client = imaplib.IMAP4_SSL(host, port) if use_ssl else imaplib.IMAP4(host, port)
    created = 0
    try:
        client.login(username, password)
        client.select(folder, readonly=True)
        status, data = client.search(None, "ALL")
        if status != "OK":
            raise RuntimeError(f"IMAP search failed: {status}")
        ids = data[0].split() if data and data[0] else []
        for msg_id in ids[-limit:]:
            status, msg_data = client.fetch(msg_id, "(RFC822)")
            if status != "OK" or not msg_data or not msg_data[0]:
                continue
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)
            message_id = _decode_header(msg.get("Message-ID")) or f"imap-{msg_id.decode()}"
            from_header = _decode_header(msg.get("From"))
            _, from_addr = email.utils.parseaddr(from_header)
            subject = _decode_header(msg.get("Subject")) or "(без темы)"
            body = _message_body(msg)[:8000]
            date_tuple = email.utils.parsedate_tz(msg.get("Date"))
            if date_tuple:
                ts = email.utils.mktime_tz(date_tuple)
                occurred = datetime.fromtimestamp(ts, tz=dt_timezone.utc)
            else:
                occurred = timezone.now()
            person = _find_person_by_email(connection.workspace, from_addr)
            activity = ingest_activity(
                connection.workspace,
                kind=Activity.Kind.EMAIL,
                channel=Activity.Channel.EMAIL,
                direction=Activity.Direction.INBOUND,
                external_id=message_id[:255],
                subject=subject,
                body=body,
                occurred_at=occurred,
                person=person,
            )
            if activity:
                created += 1
    finally:
        try:
            client.logout()
        except Exception:  # noqa: BLE001
            pass

    connection.last_synced_at = timezone.now()
    connection.last_error = ""
    connection.save(update_fields=["last_synced_at", "last_error", "updated_at"])
    return {"created": created, "provider": "imap"}


def sync_telegram_connection(connection: ChannelConnection) -> dict:
    cfg = connection.config or {}
    token = (cfg.get("bot_token") or "").strip()
    if not token:
        raise ValueError("Telegram bot_token is required.")
    offset = int(cfg.get("offset") or 0)
    url = f"https://api.telegram.org/bot{token}/getUpdates?timeout=0"
    if offset:
        url += f"&offset={offset}"
    request = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode())
    if not payload.get("ok"):
        raise RuntimeError(payload.get("description") or "Telegram API error")

    created = 0
    max_update = offset
    for update in payload.get("result") or []:
        update_id = int(update.get("update_id") or 0)
        max_update = max(max_update, update_id + 1)
        message = update.get("message") or update.get("edited_message") or {}
        text = (message.get("text") or message.get("caption") or "").strip()
        if not text:
            continue
        chat = message.get("chat") or {}
        from_user = message.get("from") or {}
        username = from_user.get("username") or ""
        external_id = f"tg-{message.get('message_id')}-{chat.get('id')}"
        person = _find_person_by_telegram(connection.workspace, username)
        if person is None and from_user.get("id"):
            person = _find_person_by_telegram(
                connection.workspace, str(from_user.get("id"))
            )
        name = " ".join(
            filter(
                None,
                [from_user.get("first_name"), from_user.get("last_name")],
            )
        ) or username or "Telegram"
        occurred = timezone.now()
        if message.get("date"):
            occurred = datetime.fromtimestamp(
                int(message["date"]), tz=dt_timezone.utc
            )
        activity = ingest_activity(
            connection.workspace,
            kind=Activity.Kind.TELEGRAM,
            channel=Activity.Channel.TELEGRAM,
            direction=Activity.Direction.INBOUND,
            external_id=external_id[:255],
            subject=f"TG: {name}",
            body=text[:8000],
            occurred_at=occurred,
            person=person,
        )
        if activity:
            created += 1

    cfg["offset"] = max_update
    connection.config = cfg
    connection.last_synced_at = timezone.now()
    connection.last_error = ""
    connection.save(update_fields=["config", "last_synced_at", "last_error", "updated_at"])
    return {"created": created, "provider": "telegram", "offset": max_update}


def ingest_telegram_webhook(connection: ChannelConnection, update: dict) -> Activity | None:
    """Process a single Telegram update payload (webhook mode)."""
    message = update.get("message") or update.get("edited_message") or {}
    text = (message.get("text") or message.get("caption") or "").strip()
    if not text:
        return None
    chat = message.get("chat") or {}
    from_user = message.get("from") or {}
    username = from_user.get("username") or ""
    external_id = f"tg-{message.get('message_id')}-{chat.get('id')}"
    person = _find_person_by_telegram(connection.workspace, username)
    name = " ".join(
        filter(None, [from_user.get("first_name"), from_user.get("last_name")])
    ) or username or "Telegram"
    occurred = timezone.now()
    if message.get("date"):
        occurred = datetime.fromtimestamp(int(message["date"]), tz=dt_timezone.utc)
    return ingest_activity(
        connection.workspace,
        kind=Activity.Kind.TELEGRAM,
        channel=Activity.Channel.TELEGRAM,
        direction=Activity.Direction.INBOUND,
        external_id=external_id[:255],
        subject=f"TG: {name}",
        body=text[:8000],
        occurred_at=occurred,
        person=person,
    )


def sync_connection(connection: ChannelConnection) -> dict:
    try:
        if connection.provider == ChannelConnection.Provider.IMAP:
            return sync_imap_connection(connection)
        if connection.provider == ChannelConnection.Provider.TELEGRAM:
            return sync_telegram_connection(connection)
        raise ValueError(f"Unknown provider: {connection.provider}")
    except Exception as exc:  # noqa: BLE001
        connection.last_error = str(exc)[:2000]
        connection.save(update_fields=["last_error", "updated_at"])
        logger.exception("Channel sync failed for %s", connection.id)
        raise


def sync_all_active_connections() -> dict:
    stats = {"connections": 0, "created": 0, "errors": 0}
    qs = ChannelConnection.objects.filter(is_active=True).select_related("workspace")
    for connection in qs:
        stats["connections"] += 1
        try:
            result = sync_connection(connection)
            stats["created"] += int(result.get("created") or 0)
        except Exception:  # noqa: BLE001
            stats["errors"] += 1
    return stats
