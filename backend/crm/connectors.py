"""On-demand CRM connectors: Stripe, 1C, WhatsApp, SMS, telephony."""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import secrets
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone as dt_timezone
from decimal import Decimal

from django.db import IntegrityError
from django.utils import timezone

from crm.models import Activity, CrmDocument, Deal, IntegrationConnector, Person
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
    {
        "provider": "telephony",
        "label": "Telephony / PBX",
        "config_keys": [
            "pbx",
            "api_key",
            "api_salt",
            "extension",
            "line_number",
            "ari_base_url",
            "ari_user",
            "ari_password",
            "endpoint",
            "context",
            "ari_app",
            "ari_subscribe_all",
            "from_number",
            "dial_url",
            "webhook_secret",
        ],
        "supports_sync": False,
        "supports_webhook": True,
        "supports_send": True,
        "supports_ari_bridge": True,
        "pbx_backends": ["asterisk", "mango", "generic"],
    },
]


def new_webhook_token() -> str:
    return secrets.token_urlsafe(24)


def _http_json(
    url: str,
    *,
    headers: dict | None = None,
    data: dict | None = None,
    method: str | None = None,
):
    body = None
    req_headers = {"Accept": "application/json", **(headers or {})}
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        req_headers["Content-Type"] = "application/json"
    verb = method or ("GET" if data is None else "POST")
    req = urllib.request.Request(url, data=body, headers=req_headers, method=verb)
    with urllib.request.urlopen(req, timeout=20) as resp:
        raw = resp.read().decode("utf-8")
        return json.loads(raw) if raw else {}


def _http_form(url: str, *, fields: dict, headers: dict | None = None) -> dict | str:
    body = urllib.parse.urlencode(fields).encode("utf-8")
    req_headers = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/x-www-form-urlencoded",
        **(headers or {}),
    }
    req = urllib.request.Request(url, data=body, headers=req_headers, method="POST")
    with urllib.request.urlopen(req, timeout=20) as resp:
        raw = resp.read().decode("utf-8")
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw


def _basic_auth(user: str, password: str) -> str:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return f"Basic {token}"


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
    deal=None,
    organization=None,
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
            deal=deal,
            organization=organization,
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


def _request_payload_dict(request) -> dict:
    data = request.data
    if hasattr(data, "dict"):
        # QueryDict → flat dict (last value wins)
        return {key: data.get(key) for key in data.keys()}
    if isinstance(data, dict):
        return dict(data)
    return {}


def verify_mango_sign(connector: IntegrationConnector, payload: dict) -> bool:
    """Validate Mango Office VPBX notification signature when api_salt is configured."""
    config = connector.config or {}
    api_key = str(config.get("api_key") or "")
    api_salt = str(config.get("api_salt") or "")
    if not api_salt:
        return True
    if not api_key:
        return False
    got_key = str(payload.get("vpbx_api_key") or payload.get("api_key") or "")
    raw_json = payload.get("json")
    if not isinstance(raw_json, str):
        # Some senders wrap the event body without a separate json field.
        body = {k: v for k, v in payload.items() if k not in ("sign", "vpbx_api_key", "api_key")}
        raw_json = json.dumps(body, ensure_ascii=False, separators=(",", ":"))
    got_sign = str(payload.get("sign") or "").lower()
    if not got_sign:
        return False
    if got_key and not secrets.compare_digest(got_key, api_key):
        return False
    expected = hashlib.sha256(f"{api_key}{raw_json}{api_salt}".encode("utf-8")).hexdigest()
    return secrets.compare_digest(got_sign, expected)


def verify_connector_webhook(connector: IntegrationConnector, request) -> bool:
    """Provider-aware webhook auth (shared secret and/or Mango sign)."""
    if not verify_webhook_secret(connector, request):
        return False
    if connector.provider != IntegrationConnector.Provider.TELEPHONY:
        return True
    config = connector.config or {}
    pbx = str(config.get("pbx") or config.get("provider") or "").strip().lower()
    if pbx in ("mango", "mango_office", "vpbx") or config.get("api_salt"):
        return verify_mango_sign(connector, _request_payload_dict(request))
    return True


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


def _party_number(value) -> str:
    if isinstance(value, dict):
        return str(
            value.get("number")
            or value.get("extension")
            or value.get("phone")
            or value.get("endpoint")
            or ""
        )
    return str(value or "")


_ARI_NOISE = {
    "ChannelVarset",
    "ChannelDialplan",
    "ChannelCallerId",
    "ChannelConnectedLine",
    "ChannelHold",
    "ChannelUnhold",
    "ChannelToneDetect",
    "DeviceStateChanged",
    "PeerStatusChange",
}
_AMI_NOISE = {"VarSet", "Newexten", "NewAccountCode", "RTCPSent", "RTCPReceived"}


def _unwrap_asterisk_event(data: dict) -> dict | None:
    """Flatten Asterisk ARI or AMI event into generic telephony fields."""
    # ARI WebSocket / webhook event
    event_type = str(data.get("type") or "")
    if event_type:
        if event_type in _ARI_NOISE:
            return None
        channel = data.get("channel") if isinstance(data.get("channel"), dict) else {}
        peer = data.get("peer") if isinstance(data.get("peer"), dict) else {}
        caller = data.get("caller") if isinstance(data.get("caller"), dict) else {}
        if not caller and channel:
            caller = channel.get("caller") if isinstance(channel.get("caller"), dict) else {}
        connected = {}
        if channel:
            connected = (
                channel.get("connected")
                if isinstance(channel.get("connected"), dict)
                else {}
            )
        dialplan = channel.get("dialplan") if isinstance(channel.get("dialplan"), dict) else {}
        if event_type == "ChannelStateChange":
            state = str(channel.get("state") or "")
            if state not in ("Ring", "Ringing", "Up"):
                return None
        call_id = str(
            channel.get("id")
            or peer.get("id")
            or data.get("asterisk_id")
            or data.get("bridge_id")
            or ""
        )
        from_phone = _party_number(caller) or _party_number(channel.get("caller"))
        to_phone = (
            _party_number(connected)
            or _party_number((peer.get("caller") if peer else None))
            or str(dialplan.get("exten") or "")
        )
        status = str(
            channel.get("state")
            or data.get("dialstatus")
            or data.get("cause_txt")
            or event_type
        )
        direction = ""
        endpoint = str(channel.get("name") or "")
        if endpoint.startswith(("PJSIP/", "SIP/", "Local/")) and to_phone and from_phone:
            # Heuristic: trunk names often contain "trunk" / DID contexts inbound
            context = str(dialplan.get("context") or "").lower()
            if "from-trunk" in context or "from-pstn" in context or "inbound" in context:
                direction = "inbound"
            elif "from-internal" in context or "outbound" in context:
                direction = "outbound"
        return {
            "call_id": call_id,
            "from": from_phone,
            "to": to_phone,
            "status": status,
            "duration": data.get("duration") or data.get("billsec") or "",
            "direction": direction,
            "source": "ari",
            "event": event_type,
        }

    # AMI Event: ...
    ami_event = str(data.get("Event") or data.get("event") or "")
    if ami_event:
        if ami_event in _AMI_NOISE:
            return None
        call_id = str(
            data.get("Uniqueid")
            or data.get("Linkedid")
            or data.get("uniqueid")
            or data.get("Channel")
            or ""
        )
        from_phone = str(
            data.get("CallerIDNum")
            or data.get("CallerID")
            or data.get("Src")
            or data.get("source")
            or ""
        )
        to_phone = str(
            data.get("ConnectedLineNum")
            or data.get("DestCallerIDNum")
            or data.get("Destination")
            or data.get("Exten")
            or data.get("Dst")
            or data.get("dialstring")
            or ""
        )
        status = str(
            data.get("ChannelStateDesc")
            or data.get("DialStatus")
            or data.get("Cause-txt")
            or data.get("Cause")
            or ami_event
        )
        direction = str(data.get("Direction") or data.get("direction") or "").lower()
        context = str(data.get("Context") or "").lower()
        if not direction:
            if "from-trunk" in context or "from-pstn" in context:
                direction = "inbound"
            elif "from-internal" in context:
                direction = "outbound"
        return {
            "call_id": call_id,
            "from": from_phone,
            "to": to_phone,
            "status": status,
            "duration": data.get("BillableSeconds")
            or data.get("billsec")
            or data.get("Duration")
            or "",
            "direction": direction,
            "source": "ami",
            "event": ami_event,
        }
    return None


def normalize_telephony_payload(payload: dict) -> dict:
    """Normalize generic / Asterisk AMI·ARI / CDR / Mango Office call events."""
    data = dict(payload or {})
    # Mango often posts form fields: json + vpbx_api_key + sign
    raw_json = data.get("json")
    if isinstance(raw_json, str) and raw_json.strip().startswith(("{", "[")):
        try:
            nested = json.loads(raw_json)
            if isinstance(nested, dict):
                data = {**data, **nested}
        except json.JSONDecodeError:
            pass

    asterisk = _unwrap_asterisk_event(data)
    if asterisk is not None:
        return asterisk

    call_id = str(
        data.get("call_id")
        or data.get("entry_id")
        or data.get("uniqueid")
        or data.get("linkedid")
        or data.get("CallSid")
        or data.get("id")
        or data.get("uuid")
        or data.get("channel")
        or ""
    )
    from_phone = _party_number(
        data.get("from") or data.get("From") or data.get("caller") or data.get("src")
    )
    to_phone = _party_number(
        data.get("to") or data.get("To") or data.get("callee") or data.get("dst")
    )
    status = str(
        data.get("status")
        or data.get("call_state")
        or data.get("CallStatus")
        or data.get("disposition")
        or ""
    )
    duration = (
        data.get("duration")
        or data.get("Duration")
        or data.get("billsec")
        or data.get("talk_time")
        or ""
    )
    direction_raw = str(data.get("direction") or data.get("Direction") or "").lower()
    location = str(data.get("location") or "").lower()
    from_obj = data.get("from")
    to_obj = data.get("to")
    if not direction_raw and isinstance(from_obj, dict) and isinstance(to_obj, dict):
        if from_obj.get("extension") and to_obj.get("number") and not to_obj.get("extension"):
            direction_raw = "outbound"
        elif from_obj.get("number") and to_obj.get("extension"):
            direction_raw = "inbound"
        elif from_obj.get("extension") and to_obj.get("number"):
            direction_raw = "outbound"
    if not direction_raw:
        if location in ("abonent",) and from_phone and not to_phone:
            direction_raw = "outbound"
        elif data.get("dst") and data.get("src"):
            direction_raw = "inbound"
        else:
            direction_raw = "inbound"
    return {
        "call_id": call_id,
        "from": from_phone,
        "to": to_phone,
        "status": status,
        "duration": duration,
        "direction": direction_raw,
        "source": "generic",
        "event": "",
    }


def _ingest_one_telephony_event(connector: IntegrationConnector, payload: dict) -> dict:
    norm = normalize_telephony_payload(payload if isinstance(payload, dict) else {})
    if norm.get("source") in ("ari", "ami") and not norm.get("call_id") and not (
        norm.get("from") or norm.get("to")
    ):
        return {"created": 0, "skipped": True, "reason": "empty asterisk event"}
    call_id = norm["call_id"]
    direction_raw = norm["direction"]
    if direction_raw in ("out", "outbound", "outgoing"):
        direction = Activity.Direction.OUTBOUND
    else:
        direction = Activity.Direction.INBOUND
    from_phone = norm["from"]
    to_phone = norm["to"]
    status = norm["status"]
    duration = norm["duration"]
    peer = from_phone if direction == Activity.Direction.INBOUND else to_phone
    if not call_id:
        call_id = f"{from_phone}:{to_phone}:{hash(status) & 0xFFFFFFFF}"
    body_parts = [
        f"from={from_phone}" if from_phone else "",
        f"to={to_phone}" if to_phone else "",
        f"status={status}" if status else "",
        f"duration={duration}s" if duration != "" else "",
        f"via={norm.get('source')}" if norm.get("source") else "",
        f"event={norm.get('event')}" if norm.get("event") else "",
    ]
    body = "; ".join(p for p in body_parts if p)
    person = find_person_by_phone(connector.workspace, peer) if peer else None
    activity = ensure_activity(
        connector.workspace,
        kind=Activity.Kind.CALL,
        channel=Activity.Channel.TELEPHONY,
        direction=direction,
        external_id=f"tel:{call_id}",
        subject=f"Call {direction} {peer or call_id}",
        body=body,
        person=person,
    )
    return {
        "created": 1 if activity else 0,
        "provider": "telephony",
        "call_id": call_id,
        "source": norm.get("source") or "generic",
    }


def ingest_telephony_webhook(connector: IntegrationConnector, payload: dict) -> dict:
    """Ingest PBX/telephony AMI, ARI, CDR or Mango event(s) → Activity(kind=call)."""
    data = payload if isinstance(payload, dict) else {}
    items: list = []
    if isinstance(data.get("events"), list):
        items = [e for e in data["events"] if isinstance(e, dict)]
    elif isinstance(data.get("EventList"), list):
        items = [e for e in data["EventList"] if isinstance(e, dict)]
    else:
        items = [data]

    created = 0
    last: dict = {"created": 0, "provider": "telephony"}
    skipped = 0
    for item in items:
        # Skip pure noise before unwrap when type/Event known
        et = str(item.get("type") or item.get("Event") or item.get("event") or "")
        if et in _ARI_NOISE or et in _AMI_NOISE:
            skipped += 1
            continue
        result = _ingest_one_telephony_event(connector, item)
        if result.get("skipped"):
            skipped += 1
            continue
        created += int(result.get("created") or 0)
        last = result
    return {
        **last,
        "created": created,
        "events": len(items),
        "skipped": skipped,
        "provider": "telephony",
    }


def _dial_asterisk_ari(config: dict, *, to: str, note: str = "") -> dict:
    base = (config.get("ari_base_url") or "").rstrip("/")
    user = config.get("ari_user") or ""
    password = config.get("ari_password") or config.get("api_key") or ""
    endpoint = config.get("endpoint") or ""
    context = config.get("context") or "from-internal"
    if not base or not user or not password or not endpoint:
        raise ValueError(
            "Asterisk dial requires ari_base_url, ari_user, ari_password (or api_key), endpoint"
        )
    # Click-to-call: ring agent endpoint, then dial destination via dialplan.
    params = urllib.parse.urlencode(
        {
            "endpoint": endpoint,
            "extension": to,
            "context": context,
            "priority": "1",
            "callerId": config.get("from_number") or endpoint,
            "timeout": str(config.get("timeout") or 30),
        }
    )
    url = f"{base}/channels?{params}"
    result = _http_json(
        url,
        headers={"Authorization": _basic_auth(user, password)},
        method="POST",
    )
    channel_id = str((result or {}).get("id") or "")
    return {
        "remote": True,
        "pbx": "asterisk",
        "channel_id": channel_id,
        "note": note,
    }


def _dial_mango(config: dict, *, to: str, note: str = "") -> dict:
    api_key = config.get("api_key") or ""
    api_salt = config.get("api_salt") or ""
    extension = str(config.get("extension") or config.get("from_number") or "")
    if not api_key or not api_salt or not extension:
        raise ValueError("Mango dial requires api_key, api_salt, and extension")
    base = (config.get("base_url") or "https://app.mango-office.ru/vpbx").rstrip("/")
    command_id = f"fp-{secrets.token_hex(8)}"
    digits = "".join(ch for ch in to if ch.isdigit())
    payload = {
        "command_id": command_id,
        "from": {"extension": extension},
        "to_number": digits or to,
    }
    if config.get("line_number"):
        payload["line_number"] = config["line_number"]
    if note:
        payload["command_id"] = f"{command_id}:{note[:40]}"
    json_body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    sign = hashlib.sha256(f"{api_key}{json_body}{api_salt}".encode("utf-8")).hexdigest()
    result = _http_form(
        f"{base}/commands/callback",
        fields={
            "vpbx_api_key": api_key,
            "sign": sign,
            "json": json_body,
        },
    )
    return {
        "remote": True,
        "pbx": "mango",
        "command_id": command_id,
        "result": result,
    }


def _dial_generic(config: dict, *, to: str, note: str = "") -> dict:
    endpoint = config.get("dial_url") or ""
    api_key = config.get("api_key") or ""
    from_number = config.get("from_number") or ""
    if not endpoint:
        return {"remote": False, "queued_locally": True, "pbx": "generic"}
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    _http_json(
        endpoint,
        headers=headers,
        data={"to": to, "from": from_number, "note": note},
    )
    return {"remote": True, "pbx": "generic"}


def dial_telephony(
    connector: IntegrationConnector,
    *,
    to: str,
    note: str = "",
    person_id: int | None = None,
    deal_id: int | None = None,
    lead_id: int | None = None,
) -> dict:
    config = connector.config or {}
    if not to:
        raise ValueError("to is required")
    pbx = str(config.get("pbx") or config.get("provider") or "generic").strip().lower()
    external_id = f"tel:out:{secrets.token_hex(8)}"
    person = None
    if person_id:
        person = Person.objects.filter(
            workspace=connector.workspace, pk=person_id
        ).first()
    if person is None:
        person = find_person_by_phone(connector.workspace, to)
    deal = None
    if deal_id:
        deal = Deal.objects.filter(workspace=connector.workspace, pk=deal_id).first()
        if deal and person is None and deal.person_id:
            person = deal.person
    body = note or f"Outbound dial via {pbx}"
    if lead_id:
        body = f"{body}; lead_id={lead_id}".strip("; ")
    ensure_activity(
        connector.workspace,
        kind=Activity.Kind.CALL,
        channel=Activity.Channel.TELEPHONY,
        direction=Activity.Direction.OUTBOUND,
        external_id=external_id,
        subject=f"Call to {to}",
        body=body,
        person=person,
        deal=deal,
        organization=deal.organization if deal else None,
    )
    try:
        if pbx in ("asterisk", "ari"):
            remote = _dial_asterisk_ari(config, to=to, note=note)
        elif pbx in ("mango", "mango_office", "vpbx"):
            remote = _dial_mango(config, to=to, note=note)
        else:
            remote = _dial_generic(config, to=to, note=note)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError) as exc:
        raise RuntimeError(f"Telephony dial failed: {exc}") from exc
    return {
        "dialed": True,
        "provider": "telephony",
        "external_id": external_id,
        "lead_id": lead_id,
        **remote,
    }


def sync_connector(connector: IntegrationConnector) -> dict:
    if connector.provider == IntegrationConnector.Provider.STRIPE:
        return sync_stripe(connector)
    if connector.provider == IntegrationConnector.Provider.ONEC:
        return sync_onec(connector)
    if connector.provider == IntegrationConnector.Provider.WHATSAPP:
        return {"created": 0, "provider": "whatsapp", "hint": "Use webhook"}
    if connector.provider == IntegrationConnector.Provider.SMS:
        return {"created": 0, "provider": "sms", "hint": "Use webhook or send"}
    if connector.provider == IntegrationConnector.Provider.TELEPHONY:
        from crm.ari_bridge import bridge_status

        status = bridge_status(connector)
        return {
            "created": 0,
            "provider": "telephony",
            "hint": "Use webhook, dial, or run_ari_bridge for live ARI events",
            "ari_bridge": status,
        }
    raise ValueError(f"Unknown provider: {connector.provider}")
