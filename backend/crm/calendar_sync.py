"""Push CRM calendar events to Google Calendar / Microsoft Graph."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.utils import timezone

from crm.calendar_events import iter_sync_payloads
from crm.models import CalendarConnection, CalendarEventLink

logger = logging.getLogger("fast_plan")

MS_SCOPES = "offline_access openid profile email User.Read Calendars.ReadWrite"
GOOGLE_SCOPES = "openid email profile https://www.googleapis.com/auth/calendar.events"


def _http_json(url: str, *, data: dict | None = None, headers: dict | None = None, method: str | None = None):
    body = None
    req_headers = {"Accept": "application/json", **(headers or {})}
    http_method = method
    if data is not None and method is None:
        http_method = "POST"
    if data is not None:
        if req_headers.get("Content-Type") == "application/json":
            body = json.dumps(data).encode("utf-8")
        else:
            body = urllib.parse.urlencode(data).encode("utf-8")
            req_headers.setdefault(
                "Content-Type", "application/x-www-form-urlencoded"
            )
    req = urllib.request.Request(
        url, data=body, headers=req_headers, method=http_method or "GET"
    )
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
        raw = resp.read().decode("utf-8")
        return json.loads(raw) if raw else {}


def provider_configured(provider: str) -> bool:
    if provider == CalendarConnection.Provider.MICROSOFT:
        return bool(
            getattr(settings, "OAUTH_MICROSOFT_CLIENT_ID", "").strip()
            and getattr(settings, "OAUTH_MICROSOFT_CLIENT_SECRET", "").strip()
        )
    if provider == CalendarConnection.Provider.GOOGLE:
        return bool(
            getattr(settings, "OAUTH_GOOGLE_CLIENT_ID", "").strip()
            and getattr(settings, "OAUTH_GOOGLE_CLIENT_SECRET", "").strip()
        )
    return False


def ensure_access_token(connection: CalendarConnection) -> str:
    if (
        connection.access_token
        and connection.token_expires_at
        and connection.token_expires_at > timezone.now() + timedelta(minutes=2)
    ):
        return connection.access_token
    if not connection.refresh_token:
        raise ValueError("No refresh token — reconnect calendar")

    if connection.provider == CalendarConnection.Provider.MICROSOFT:
        token = _http_json(
            "https://login.microsoftonline.com/common/oauth2/v2.0/token",
            data={
                "client_id": settings.OAUTH_MICROSOFT_CLIENT_ID,
                "client_secret": settings.OAUTH_MICROSOFT_CLIENT_SECRET,
                "refresh_token": connection.refresh_token,
                "grant_type": "refresh_token",
                "scope": MS_SCOPES,
            },
        )
    else:
        token = _http_json(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": settings.OAUTH_GOOGLE_CLIENT_ID,
                "client_secret": settings.OAUTH_GOOGLE_CLIENT_SECRET,
                "refresh_token": connection.refresh_token,
                "grant_type": "refresh_token",
            },
        )

    access = token.get("access_token")
    if not access:
        raise ValueError("Token refresh failed")
    connection.access_token = access
    if token.get("refresh_token"):
        connection.refresh_token = token["refresh_token"]
    expires_in = int(token.get("expires_in") or 3600)
    connection.token_expires_at = timezone.now() + timedelta(seconds=expires_in)
    connection.save(
        update_fields=["access_token", "refresh_token", "token_expires_at", "updated_at"]
    )
    return access


def _ms_event_body(payload: dict) -> dict:
    start = payload["start"]
    end = payload["end"]
    if payload.get("all_day"):
        day = start.date().isoformat()
        end_day = (start.date() + timedelta(days=1)).isoformat()
        return {
            "subject": payload["title"],
            "body": {"contentType": "Text", "content": payload.get("body") or ""},
            "isAllDay": True,
            "start": {"dateTime": f"{day}T00:00:00", "timeZone": "UTC"},
            "end": {"dateTime": f"{end_day}T00:00:00", "timeZone": "UTC"},
        }
    return {
        "subject": payload["title"],
        "body": {"contentType": "Text", "content": payload.get("body") or ""},
        "start": {
            "dateTime": start.strftime("%Y-%m-%dT%H:%M:%S"),
            "timeZone": "UTC",
        },
        "end": {
            "dateTime": (end + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S"),
            "timeZone": "UTC",
        },
    }


def _google_event_body(payload: dict) -> dict:
    start = payload["start"]
    if payload.get("all_day"):
        day = start.date().isoformat()
        end_day = (start.date() + timedelta(days=1)).isoformat()
        return {
            "summary": payload["title"],
            "description": payload.get("body") or "",
            "start": {"date": day},
            "end": {"date": end_day},
        }
    end = payload["end"] + timedelta(hours=1)
    return {
        "summary": payload["title"],
        "description": payload.get("body") or "",
        "start": {"dateTime": start.isoformat() + "Z"},
        "end": {"dateTime": end.isoformat() + "Z"},
    }


def _upsert_external(connection: CalendarConnection, access: str, payload: dict) -> str:
    link = CalendarEventLink.objects.filter(
        connection=connection,
        source_type=payload["source_type"],
        source_id=payload["source_id"],
    ).first()

    if connection.provider == CalendarConnection.Provider.MICROSOFT:
        body = _ms_event_body(payload)
        cal = connection.external_calendar_id or None
        base = (
            f"https://graph.microsoft.com/v1.0/me/calendars/{cal}/events"
            if cal
            else "https://graph.microsoft.com/v1.0/me/events"
        )
        headers = {
            "Authorization": f"Bearer {access}",
            "Content-Type": "application/json",
        }
        if link:
            result = _http_json(
                f"{base}/{link.external_event_id}",
                data=body,
                headers=headers,
                method="PATCH",
            )
            return result.get("id") or link.external_event_id
        result = _http_json(base, data=body, headers=headers)
        return str(result["id"])

    # Google
    body = _google_event_body(payload)
    cal_id = urllib.parse.quote(connection.external_calendar_id or "primary")
    headers = {
        "Authorization": f"Bearer {access}",
        "Content-Type": "application/json",
    }
    if link:
        url = (
            f"https://www.googleapis.com/calendar/v3/calendars/{cal_id}/events/"
            f"{urllib.parse.quote(link.external_event_id)}"
        )
        result = _http_json(url, data=body, headers=headers, method="PATCH")
        return result.get("id") or link.external_event_id
    url = f"https://www.googleapis.com/calendar/v3/calendars/{cal_id}/events"
    result = _http_json(url, data=body, headers=headers)
    return str(result["id"])


def sync_connection(connection: CalendarConnection) -> dict[str, Any]:
    try:
        access = ensure_access_token(connection)
        payloads = iter_sync_payloads(connection.workspace)
        pushed = 0
        for payload in payloads:
            external_id = _upsert_external(connection, access, payload)
            CalendarEventLink.objects.update_or_create(
                connection=connection,
                source_type=payload["source_type"],
                source_id=payload["source_id"],
                defaults={"external_event_id": external_id},
            )
            pushed += 1
        connection.last_synced_at = timezone.now()
        connection.last_error = ""
        connection.save(update_fields=["last_synced_at", "last_error", "updated_at"])
        return {"ok": True, "pushed": pushed}
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError, KeyError) as exc:
        logger.warning("Calendar sync failed for %s: %s", connection.id, exc)
        connection.last_error = str(exc)[:500]
        connection.save(update_fields=["last_error", "updated_at"])
        return {"ok": False, "error": str(exc), "pushed": 0}
