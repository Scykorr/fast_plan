"""Live Asterisk ARI WebSocket bridge → telephony Activity ingest."""

from __future__ import annotations

import asyncio
import json
import logging
import urllib.parse
from typing import Any

from django.utils import timezone

from crm.connectors import ingest_telephony_webhook
from crm.models import IntegrationConnector

logger = logging.getLogger("fast_plan")


def ari_events_ws_url(config: dict) -> str:
    """Build ARI /events WebSocket URL from connector config."""
    base = (config.get("ari_base_url") or "").rstrip("/")
    if not base:
        raise ValueError("ari_base_url is required")
    user = config.get("ari_user") or ""
    password = config.get("ari_password") or config.get("api_key") or ""
    if not user or not password:
        raise ValueError("ari_user and ari_password (or api_key) are required")
    app = (config.get("ari_app") or "fast-plan").strip() or "fast-plan"
    subscribe_all = str(config.get("ari_subscribe_all") or "true").lower() in (
        "1",
        "true",
        "yes",
    )
    if base.startswith("https://"):
        ws_base = "wss://" + base[len("https://") :]
    elif base.startswith("http://"):
        ws_base = "ws://" + base[len("http://") :]
    elif base.startswith(("ws://", "wss://")):
        ws_base = base
    else:
        ws_base = "ws://" + base
    # ari_base_url is typically …/ari — events live at …/ari/events
    if not ws_base.rstrip("/").endswith("/ari"):
        if "/ari/" in ws_base:
            pass
        else:
            ws_base = ws_base.rstrip("/") + "/ari"
    params = {
        "app": app,
        "api_key": f"{user}:{password}",
        "subscribeAll": "true" if subscribe_all else "false",
    }
    return f"{ws_base.rstrip('/')}/events?{urllib.parse.urlencode(params)}"


def process_ari_message(connector: IntegrationConnector, raw: str | bytes | dict) -> dict:
    """Parse one ARI WS frame and ingest into CRM."""
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8", errors="replace")
    if isinstance(raw, str):
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("ARI bridge: non-JSON frame for connector %s", connector.id)
            return {"created": 0, "skipped": True, "reason": "non-json"}
    else:
        payload = raw
    if not isinstance(payload, dict):
        return {"created": 0, "skipped": True, "reason": "not-object"}
    return ingest_telephony_webhook(connector, payload)


def list_asterisk_connectors(*, connector_id: int | None = None):
    qs = IntegrationConnector.objects.filter(
        provider=IntegrationConnector.Provider.TELEPHONY,
        is_active=True,
    ).select_related("workspace")
    if connector_id:
        qs = qs.filter(pk=connector_id)
    rows = []
    for row in qs:
        pbx = str((row.config or {}).get("pbx") or "").lower()
        if pbx in ("asterisk", "ari") and (row.config or {}).get("ari_base_url"):
            rows.append(row)
    return rows


async def _bridge_one(
    connector: IntegrationConnector,
    *,
    reconnect_delay: float = 5.0,
    max_messages: int | None = None,
) -> None:
    import websockets
    from websockets.exceptions import ConnectionClosed

    config = dict(connector.config or {})
    url = ari_events_ws_url(config)
    # Redact password in logs
    safe_url = url.split("api_key=")[0] + "api_key=***"
    seen = 0
    while True:
        try:
            logger.info(
                "ARI bridge connecting connector=%s workspace=%s url=%s",
                connector.id,
                connector.workspace_id,
                safe_url,
            )
            async with websockets.connect(
                url,
                ping_interval=20,
                ping_timeout=20,
                max_size=2**20,
            ) as ws:
                connector.last_error = ""
                connector.last_synced_at = timezone.now()
                connector.save(update_fields=["last_error", "last_synced_at", "updated_at"])
                async for message in ws:
                    try:
                        result = process_ari_message(connector, message)
                        if result.get("created"):
                            connector.last_synced_at = timezone.now()
                            connector.save(
                                update_fields=["last_synced_at", "updated_at"]
                            )
                    except Exception as exc:  # noqa: BLE001
                        logger.exception(
                            "ARI bridge ingest failed connector=%s: %s",
                            connector.id,
                            exc,
                        )
                        connector.last_error = str(exc)[:2000]
                        connector.save(update_fields=["last_error", "updated_at"])
                    seen += 1
                    if max_messages is not None and seen >= max_messages:
                        return
        except ConnectionClosed as exc:
            logger.warning(
                "ARI bridge disconnected connector=%s: %s", connector.id, exc
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "ARI bridge error connector=%s: %s", connector.id, exc
            )
            connector.last_error = str(exc)[:2000]
            connector.save(update_fields=["last_error", "updated_at"])
        if max_messages is not None:
            return
        await asyncio.sleep(reconnect_delay)


async def run_bridges(
    connectors: list[IntegrationConnector],
    *,
    reconnect_delay: float = 5.0,
    max_messages: int | None = None,
) -> None:
    if not connectors:
        raise ValueError("No active Asterisk telephony connectors with ari_base_url")
    await asyncio.gather(
        *[
            _bridge_one(c, reconnect_delay=reconnect_delay, max_messages=max_messages)
            for c in connectors
        ]
    )


def bridge_status(connector: IntegrationConnector) -> dict[str, Any]:
    config = connector.config or {}
    pbx = str(config.get("pbx") or "").lower()
    ready = pbx in ("asterisk", "ari") and bool(config.get("ari_base_url"))
    try:
        url = ari_events_ws_url(config) if ready else ""
        safe = (url.split("api_key=")[0] + "api_key=***") if url else ""
    except ValueError as exc:
        return {
            "ready": False,
            "detail": str(exc),
            "pbx": pbx,
            "command": "python manage.py run_ari_bridge --connector-id "
            f"{connector.id}",
        }
    return {
        "ready": ready,
        "pbx": pbx,
        "ari_app": config.get("ari_app") or "fast-plan",
        "ws_url": safe,
        "last_synced_at": connector.last_synced_at,
        "last_error": connector.last_error,
        "command": f"python manage.py run_ari_bridge --connector-id {connector.id}",
        "hint": "Run the management command (or docker compose --profile telephony) for a live ARI WebSocket bridge.",
    }
