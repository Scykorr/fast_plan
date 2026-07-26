"""On-demand CRM connectors: Stripe, 1C, WhatsApp, SMS."""

from __future__ import annotations

import base64
import json
import logging
import secrets
import urllib.error
import urllib.request
from datetime import datetime, timezone as dt_timezone
from decimal import Decimal

from django.db import IntegrityError
from django.utils import timezone

from crm.models import Activity, CrmDocument, IntegrationConnector, Person
from finance.models import Transaction

logger = logging.getLogger("fast_plan")

CONNECTOR_CATALOG = [
    {
        "provider": "stripe",
        "label": "Stripe",
        "config_keys": ["secret_key", "webhook_secret"],
        "supports_sync": True,
        "supports_webhook": True,
    },
    {
        "provider": "onec",
        "label": "1C",
        "config_keys": ["base_url", "login", "password", "pending_documents"],
        "supports_sync": True,
        "supports_webhook": True,
    },
    {
        "provider": "whatsapp",
        "label": "WhatsApp",
        "config_keys": [
            "access_token",
            "phone_number_id",
            "verify_token",
            "webhook_secret",
        ],
        "supports_sync": False,
        "supports_webhook": True,
    },
    {
        "provider": "sms",
        "label": "SMS",
        "config_keys": ["provider", "api_key", "from_number", "webhook_secret"],
        "supports_sync": False,
        "supports_webhook": True,
        "supports_send": True,
    },
]


def new_webhook_token() -> str:
    return secrets.token_urlsafe(24)


def _http_json(url: str, *, headers: dict | None = None, data: dict | None = None):
    body = None
    req_headers = {"Accept": "application/json", **(headers or {})}
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        req_headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=req_headers, method="GET" if data is None else "POST")
    with urllib.request.urlopen(req, timeout=20) as resp:
        raw = resp.read().decode("utf-8")
        return json.loads(raw) if raw else {}


def ensure_activity(
    workspace,
    *,
    kind: str,
    channel: str,
    direction: str,
    external_id: str,
    subject: str,
    body: str = "",
    person: Person | None = None,
    occurred_at=None,
) -> Activity | None:
    if not external_id:
        return None
    try:
        return Activity.objects.create(
            workspace=workspace,
            kind=kind,
            channel=channel,
            direction=direction,
            external_id=external_id,
            subject=subject[:255],
            body=body or "",
            occurred_at=occurred_at or timezone.now(),
            person=person,
        )
    except IntegrityError:
        return None


def find_person_by_phone(workspace, phone: str) -> Person | None:
    digits = "".join(ch for ch in (phone or "") if ch.isdigit())
    if len(digits) < 7:
        return None
    for person in Person.objects.filter(workspace=workspace).exclude(phone=""):
        pdigits = "".join(ch for ch in person.phone if ch.isdigit())
        if pdigits and (pdigits.endswith(digits[-10:]) or digits.endswith(pdigits[-10:])):
            return person
    return None


def verify_webhook_secret(connector: IntegrationConnector, request) -> bool:
    expected = (connector.config or {}).get("webhook_secret") or ""
    if not expected:
        return True
    got = (
        request.headers.get("X-Webhook-Secret")
        or request.headers.get("X-Connector-Secret")
        or request.query_params.get("secret")
        or ""
    )
    return secrets.compare_digest(str(got), str(expected))


def sync_stripe(connector: IntegrationConnector) -> dict:
    secret = (connector.config or {}).get("secret_key") or ""
    if not secret:
        return {"created": 0, "skipped": True, "reason": "secret_key not set"}
    auth = base64.b64encode(f"{secret}:".encode()).decode()
    try:
        payload = _http_json(
            "https://api.stripe.com/v1/charges?limit=20",
            headers={"Authorization": f"Basic {auth}"},
        )
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Stripe API error: {exc}") from exc

    created = 0
    for charge in payload.get("data") or []:
        if not charge.get("paid"):
            continue
        cid = charge.get("id") or ""
        amount = Decimal(charge.get("amount") or 0) / Decimal("100")
        currency = (charge.get("currency") or "rub").upper()
        external_id = f"stripe:charge:{cid}"
        activity = ensure_activity(
            connector.workspace,
            kind=Activity.Kind.PAYMENT,
            channel=Activity.Channel.STRIPE,
            direction=Activity.Direction.INBOUND,
            external_id=external_id,
            subject=f"Stripe charge {cid}",
            body=f"{amount} {currency}",
            occurred_at=datetime.fromtimestamp(
                charge.get("created") or timezone.now().timestamp(),
                tz=dt_timezone.utc,
            ),
        )
        if activity is None:
            continue
        created += 1
        if not Transaction.objects.filter(
            workspace=connector.workspace,
            notes__contains=external_id,
        ).exists():
            Transaction.objects.create(
                workspace=connector.workspace,
                title=f"Stripe {cid}",
                amount=amount,
                transaction_type=Transaction.TransactionType.INCOME,
                category="stripe",
                transaction_date=timezone.localdate(),
                notes=external_id,
            )
    return {"created": created, "provider": "stripe"}


def ingest_stripe_event(connector: IntegrationConnector, payload: dict) -> dict:
    etype = payload.get("type") or ""
    obj = (payload.get("data") or {}).get("object") or {}
    if etype not in (
        "charge.succeeded",
        "payment_intent.succeeded",
        "checkout.session.completed",
    ):
        return {"created": 0, "ignored": etype}

    oid = obj.get("id") or payload.get("id") or ""
    amount_raw = obj.get("amount_received") or obj.get("amount_total") or obj.get("amount") or 0
    amount = Decimal(amount_raw) / Decimal("100")
    external_id = f"stripe:event:{etype}:{oid}"
    activity = ensure_activity(
        connector.workspace,
        kind=Activity.Kind.PAYMENT,
        channel=Activity.Channel.STRIPE,
        direction=Activity.Direction.INBOUND,
        external_id=external_id,
        subject=f"Stripe {etype}",
        body=f"{amount}",
    )
    created = 1 if activity else 0
    if activity and amount > 0:
        Transaction.objects.get_or_create(
            workspace=connector.workspace,
            notes=external_id,
            defaults={
                "title": f"Stripe {etype}",
                "amount": amount,
                "transaction_type": Transaction.TransactionType.INCOME,
                "category": "stripe",
                "transaction_date": timezone.localdate(),
            },
        )
    return {"created": created, "provider": "stripe", "type": etype}


def sync_onec(connector: IntegrationConnector) -> dict:
    config = connector.config or {}
    pending = list(config.get("pending_documents") or [])
    created = 0
    imported = []

    if config.get("base_url") and not pending:
        url = config["base_url"].rstrip("/") + "/invoices.json"
        try:
            headers = {}
            if config.get("login"):
                token = base64.b64encode(
                    f"{config.get('login')}:{config.get('password') or ''}".encode()
                ).decode()
                headers["Authorization"] = f"Basic {token}"
            payload = _http_json(url, headers=headers)
            pending = payload if isinstance(payload, list) else payload.get("documents") or []
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
            # Soft-fail: keep local pending queue usable without live 1C
            logger.info("1C remote sync skipped: %s", exc)

    for item in pending:
        if not isinstance(item, dict):
            continue
        external_id = str(item.get("id") or item.get("number") or "")
        title = str(item.get("title") or item.get("number") or "1C document")
        amount = Decimal(str(item.get("amount") or "0"))
        doc_type = item.get("doc_type") or CrmDocument.DocType.INVOICE
        if doc_type not in {c.value for c in CrmDocument.DocType}:
            doc_type = CrmDocument.DocType.INVOICE
        if external_id and CrmDocument.objects.filter(
            workspace=connector.workspace, number=external_id
        ).exists():
            continue
        CrmDocument.objects.create(
            workspace=connector.workspace,
            doc_type=doc_type,
            number=external_id[:64],
            title=title[:255],
            amount=amount,
            status=CrmDocument.Status.SENT,
            body=str(item.get("body") or "Imported from 1C"),
            due_date=None,
        )
        ensure_activity(
            connector.workspace,
            kind=Activity.Kind.INVOICE,
            channel=Activity.Channel.ONEC,
            direction=Activity.Direction.INBOUND,
            external_id=f"onec:doc:{external_id or title}",
            subject=f"1C import: {title}",
            body=str(amount),
        )
        created += 1
        imported.append(external_id or title)

    if "pending_documents" in config:
        config = {**config, "pending_documents": []}
        connector.config = config
        connector.save(update_fields=["config", "updated_at"])

    return {"created": created, "provider": "onec", "imported": imported}


def ingest_onec_documents(connector: IntegrationConnector, payload: dict | list) -> dict:
    docs = payload if isinstance(payload, list) else payload.get("documents") or []
    config = dict(connector.config or {})
    existing = list(config.get("pending_documents") or [])
    existing.extend(docs if isinstance(docs, list) else [])
    config["pending_documents"] = existing
    connector.config = config
    connector.save(update_fields=["config", "updated_at"])
    return sync_onec(connector)


def ingest_whatsapp_webhook(connector: IntegrationConnector, payload: dict) -> dict:
    created = 0
    for entry in payload.get("entry") or []:
        for change in entry.get("changes") or []:
            value = change.get("value") or {}
            for message in value.get("messages") or []:
                mid = message.get("id") or ""
                text = ((message.get("text") or {}).get("body")) or ""
                phone = message.get("from") or ""
                person = find_person_by_phone(connector.workspace, phone)
                activity = ensure_activity(
                    connector.workspace,
                    kind=Activity.Kind.WHATSAPP,
                    channel=Activity.Channel.WHATSAPP,
                    direction=Activity.Direction.INBOUND,
                    external_id=f"wa:{mid}",
                    subject=f"WhatsApp from {phone}",
                    body=text,
                    person=person,
                )
                if activity:
                    created += 1
    return {"created": created, "provider": "whatsapp"}


def ingest_sms_webhook(connector: IntegrationConnector, payload: dict) -> dict:
    mid = str(payload.get("id") or payload.get("MessageSid") or payload.get("message_id") or "")
    phone = str(payload.get("from") or payload.get("From") or "")
    text = str(payload.get("body") or payload.get("Body") or payload.get("text") or "")
    if not mid:
        mid = f"{phone}:{hash(text) & 0xFFFFFFFF}"
    person = find_person_by_phone(connector.workspace, phone)
    activity = ensure_activity(
        connector.workspace,
        kind=Activity.Kind.SMS,
        channel=Activity.Channel.SMS,
        direction=Activity.Direction.INBOUND,
        external_id=f"sms:{mid}",
        subject=f"SMS from {phone}",
        body=text,
        person=person,
    )
    return {"created": 1 if activity else 0, "provider": "sms"}


def send_sms(connector: IntegrationConnector, *, to: str, body: str) -> dict:
    config = connector.config or {}
    api_key = config.get("api_key") or ""
    from_number = config.get("from_number") or ""
    if not to or not body:
        raise ValueError("to and body are required")
    # Record outbound activity even when remote provider is stubbed.
    ensure_activity(
        connector.workspace,
        kind=Activity.Kind.SMS,
        channel=Activity.Channel.SMS,
        direction=Activity.Direction.OUTBOUND,
        external_id=f"sms:out:{secrets.token_hex(8)}",
        subject=f"SMS to {to}",
        body=body,
        person=find_person_by_phone(connector.workspace, to),
    )
    endpoint = config.get("send_url")
    if endpoint and api_key:
        try:
            _http_json(
                endpoint,
                headers={"Authorization": f"Bearer {api_key}"},
                data={"to": to, "from": from_number, "body": body},
            )
            return {"sent": True, "provider": "sms", "remote": True}
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
            raise RuntimeError(f"SMS send failed: {exc}") from exc
    return {"sent": True, "provider": "sms", "remote": False, "queued_locally": True}


def sync_connector(connector: IntegrationConnector) -> dict:
    if connector.provider == IntegrationConnector.Provider.STRIPE:
        return sync_stripe(connector)
    if connector.provider == IntegrationConnector.Provider.ONEC:
        return sync_onec(connector)
    if connector.provider == IntegrationConnector.Provider.WHATSAPP:
        return {"created": 0, "provider": "whatsapp", "hint": "Use webhook"}
    if connector.provider == IntegrationConnector.Provider.SMS:
        return {"created": 0, "provider": "sms", "hint": "Use webhook or send"}
    raise ValueError(f"Unknown provider: {connector.provider}")
