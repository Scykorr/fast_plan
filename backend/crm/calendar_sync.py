"""Two-way CRM calendar sync with Google Calendar / Microsoft Graph."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone as dt_timezone
from typing import Any

from django.conf import settings
from django.db import IntegrityError
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from crm.calendar_events import iter_sync_payloads
from crm.models import (
    Activity,
    CalendarConnection,
    CalendarEventLink,
    CalendarSyncConflict,
)

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


def _upsert_external(connection: CalendarConnection, access: str, payload: dict) -> dict:
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
            return {
                "id": result.get("id") or link.external_event_id,
                "etag": result.get("@odata.etag") or "",
                "updated": result.get("lastModifiedDateTime"),
            }
        result = _http_json(base, data=body, headers=headers)
        return {
            "id": str(result["id"]),
            "etag": result.get("@odata.etag") or "",
            "updated": result.get("lastModifiedDateTime"),
        }

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
        return {
            "id": result.get("id") or link.external_event_id,
            "etag": result.get("etag") or "",
            "updated": result.get("updated"),
        }
    url = f"https://www.googleapis.com/calendar/v3/calendars/{cal_id}/events"
    result = _http_json(url, data=body, headers=headers)
    return {
        "id": str(result["id"]),
        "etag": result.get("etag") or "",
        "updated": result.get("updated"),
    }


def _parse_ext_dt(value: str | None):
    if not value:
        return None
    if len(value) == 10 and value[4] == "-":
        return timezone.make_aware(datetime.fromisoformat(value + "T00:00:00"))
    parsed = parse_datetime(value.replace("Z", "+00:00"))
    if parsed is None:
        return None
    if timezone.is_naive(parsed):
        return timezone.make_aware(parsed, dt_timezone.utc)
    return parsed


def list_external_events(
    connection: CalendarConnection, access: str, *, horizon_days: int = 90
) -> list[dict]:
    start = timezone.now() - timedelta(days=7)
    end = timezone.now() + timedelta(days=horizon_days)
    headers = {"Authorization": f"Bearer {access}"}

    if connection.provider == CalendarConnection.Provider.MICROSOFT:
        cal = connection.external_calendar_id or None
        base = (
            f"https://graph.microsoft.com/v1.0/me/calendars/{cal}/calendarView"
            if cal
            else "https://graph.microsoft.com/v1.0/me/calendarView"
        )
        params = urllib.parse.urlencode(
            {
                "startDateTime": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "endDateTime": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "$top": "100",
                "$orderby": "start/dateTime",
            }
        )
        payload = _http_json(f"{base}?{params}", headers=headers)
        rows = []
        for item in payload.get("value") or []:
            start_obj = item.get("start") or {}
            start_raw = start_obj.get("dateTime") or start_obj.get("date")
            rows.append(
                {
                    "id": str(item.get("id") or ""),
                    "title": item.get("subject") or "(no title)",
                    "body": ((item.get("body") or {}).get("content") or "")[:2000],
                    "start": _parse_ext_dt(start_raw),
                    "etag": item.get("@odata.etag") or "",
                    "updated": _parse_ext_dt(item.get("lastModifiedDateTime")),
                }
            )
        return [r for r in rows if r["id"]]

    cal_id = urllib.parse.quote(connection.external_calendar_id or "primary")
    params = urllib.parse.urlencode(
        {
            "timeMin": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "timeMax": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "singleEvents": "true",
            "orderBy": "startTime",
            "maxResults": "100",
        }
    )
    url = f"https://www.googleapis.com/calendar/v3/calendars/{cal_id}/events?{params}"
    payload = _http_json(url, headers=headers)
    rows = []
    for item in payload.get("items") or []:
        start_obj = item.get("start") or {}
        start_raw = start_obj.get("dateTime") or start_obj.get("date")
        rows.append(
            {
                "id": str(item.get("id") or ""),
                "title": item.get("summary") or "(no title)",
                "body": (item.get("description") or "")[:2000],
                "start": _parse_ext_dt(start_raw),
                "etag": item.get("etag") or "",
                "updated": _parse_ext_dt(item.get("updated")),
            }
        )
    return [r for r in rows if r["id"]]


def _apply_external_to_activity(activity: Activity, event: dict) -> None:
    activity.subject = (event.get("title") or activity.subject)[:255]
    activity.body = event.get("body") or activity.body
    if event.get("start"):
        activity.occurred_at = event["start"]
    activity.save(update_fields=["subject", "body", "occurred_at"])


def pull_connection(connection: CalendarConnection, access: str | None = None) -> dict[str, Any]:
    access = access or ensure_access_token(connection)
    events = list_external_events(connection, access)
    imported = 0
    updated = 0
    conflicts = 0
    skipped = 0

    for event in events:
        link = CalendarEventLink.objects.filter(
            connection=connection, external_event_id=event["id"]
        ).first()

        if link is None:
            external_key = f"cal:{connection.provider}:{event['id']}"
            try:
                activity = Activity.objects.create(
                    workspace=connection.workspace,
                    kind=Activity.Kind.MEETING,
                    channel=Activity.Channel.CALENDAR,
                    direction=Activity.Direction.INBOUND,
                    external_id=external_key[:255],
                    subject=(event.get("title") or "Calendar event")[:255],
                    body=event.get("body") or "",
                    occurred_at=event.get("start") or timezone.now(),
                    created_by=connection.user,
                )
            except IntegrityError:
                activity = Activity.objects.filter(
                    workspace=connection.workspace,
                    channel=Activity.Channel.CALENDAR,
                    external_id=external_key[:255],
                ).first()
            if activity is None:
                continue
            CalendarEventLink.objects.update_or_create(
                connection=connection,
                source_type="pulled_activity",
                source_id=str(activity.id),
                defaults={
                    "external_event_id": event["id"],
                    "external_etag": event.get("etag") or "",
                    "external_updated_at": event.get("updated"),
                    "direction": "pull",
                },
            )
            imported += 1
            continue

        if link.source_type in ("deal_task", "meeting") and link.direction != "pull":
            policy = connection.conflict_policy
            local_title = ""
            local_start = None
            if link.source_type == "meeting":
                activity = Activity.objects.filter(pk=link.source_id).first()
                if activity:
                    local_title = activity.subject
                    local_start = activity.occurred_at
            changed = bool(
                (event.get("etag") and event["etag"] != link.external_etag)
                or (event.get("title") and local_title and event["title"] != local_title)
            )
            if not changed:
                skipped += 1
                continue
            if policy == CalendarConnection.ConflictPolicy.OURS:
                skipped += 1
                continue
            if policy == CalendarConnection.ConflictPolicy.THEIRS:
                if link.source_type == "meeting":
                    activity = Activity.objects.filter(pk=link.source_id).first()
                    if activity:
                        _apply_external_to_activity(activity, event)
                        updated += 1
                link.external_etag = event.get("etag") or link.external_etag
                link.external_updated_at = event.get("updated")
                link.save(
                    update_fields=["external_etag", "external_updated_at", "updated_at"]
                )
                continue
            CalendarSyncConflict.objects.update_or_create(
                connection=connection,
                external_event_id=event["id"],
                status=CalendarSyncConflict.Status.OPEN,
                defaults={
                    "link": link,
                    "local_title": local_title,
                    "external_title": event.get("title") or "",
                    "local_start": local_start,
                    "external_start": event.get("start"),
                    "payload": {
                        "title": event.get("title"),
                        "body": event.get("body"),
                        "etag": event.get("etag"),
                    },
                },
            )
            conflicts += 1
            continue

        if link.source_type == "pulled_activity":
            activity = Activity.objects.filter(pk=link.source_id).first()
            if activity and (
                (event.get("etag") and event["etag"] != link.external_etag)
                or event.get("title") != activity.subject
            ):
                if connection.conflict_policy == CalendarConnection.ConflictPolicy.OURS:
                    skipped += 1
                elif connection.conflict_policy == CalendarConnection.ConflictPolicy.MANUAL:
                    CalendarSyncConflict.objects.update_or_create(
                        connection=connection,
                        external_event_id=event["id"],
                        status=CalendarSyncConflict.Status.OPEN,
                        defaults={
                            "link": link,
                            "local_title": activity.subject,
                            "external_title": event.get("title") or "",
                            "local_start": activity.occurred_at,
                            "external_start": event.get("start"),
                            "payload": {
                                "title": event.get("title"),
                                "body": event.get("body"),
                                "etag": event.get("etag"),
                            },
                        },
                    )
                    conflicts += 1
                else:
                    _apply_external_to_activity(activity, event)
                    link.external_etag = event.get("etag") or ""
                    link.external_updated_at = event.get("updated")
                    link.save(
                        update_fields=[
                            "external_etag",
                            "external_updated_at",
                            "updated_at",
                        ]
                    )
                    updated += 1
            else:
                skipped += 1

    return {
        "imported": imported,
        "updated": updated,
        "conflicts": conflicts,
        "skipped": skipped,
        "listed": len(events),
    }


def push_connection(connection: CalendarConnection, access: str | None = None) -> dict[str, Any]:
    access = access or ensure_access_token(connection)
    payloads = iter_sync_payloads(connection.workspace)
    pushed = 0
    for payload in payloads:
        meta = _upsert_external(connection, access, payload)
        CalendarEventLink.objects.update_or_create(
            connection=connection,
            source_type=payload["source_type"],
            source_id=payload["source_id"],
            defaults={
                "external_event_id": meta["id"],
                "external_etag": meta.get("etag") or "",
                "external_updated_at": _parse_ext_dt(meta.get("updated")),
                "direction": "push",
            },
        )
        pushed += 1
    return {"pushed": pushed}


def sync_connection(
    connection: CalendarConnection, *, direction: str = "both"
) -> dict[str, Any]:
    try:
        access = ensure_access_token(connection)
        result: dict[str, Any] = {"ok": True, "direction": direction}
        if direction in ("push", "both"):
            result.update(push_connection(connection, access))
        else:
            result["pushed"] = 0
        if direction in ("pull", "both"):
            result.update(pull_connection(connection, access))
        else:
            result.setdefault("imported", 0)
            result.setdefault("updated", 0)
            result.setdefault("conflicts", 0)
        connection.last_synced_at = timezone.now()
        connection.last_error = ""
        connection.save(update_fields=["last_synced_at", "last_error", "updated_at"])
        return result
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError, KeyError) as exc:
        logger.warning("Calendar sync failed for %s: %s", connection.id, exc)
        connection.last_error = str(exc)[:500]
        connection.save(update_fields=["last_error", "updated_at"])
        return {"ok": False, "error": str(exc), "pushed": 0, "imported": 0}


def resolve_conflict(
    conflict: CalendarSyncConflict, *, choice: str
) -> CalendarSyncConflict:
    link = conflict.link
    if choice == "dismiss":
        conflict.status = CalendarSyncConflict.Status.DISMISSED
    elif choice == "theirs" and link and link.source_type in ("meeting", "pulled_activity"):
        activity = Activity.objects.filter(pk=link.source_id).first()
        if activity:
            _apply_external_to_activity(
                activity,
                {
                    "title": conflict.external_title or conflict.payload.get("title"),
                    "body": conflict.payload.get("body") or activity.body,
                    "start": conflict.external_start,
                },
            )
        link.external_etag = conflict.payload.get("etag") or link.external_etag
        link.external_updated_at = conflict.external_start
        link.save(update_fields=["external_etag", "external_updated_at", "updated_at"])
        conflict.status = CalendarSyncConflict.Status.RESOLVED_THEIRS
    else:
        if link:
            link.external_etag = conflict.payload.get("etag") or link.external_etag
            link.save(update_fields=["external_etag", "updated_at"])
        conflict.status = CalendarSyncConflict.Status.RESOLVED_OURS
    conflict.resolved_at = timezone.now()
    conflict.save(update_fields=["status", "resolved_at"])
    return conflict
