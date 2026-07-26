"""On-demand CRM connectors (Stripe / 1C / WhatsApp / SMS / telephony)."""

import hashlib
import json

from crm.models import Activity, CrmDocument, IntegrationConnector
from finance.models import Transaction


def test_connector_catalog_and_crud(authenticated_client):
    catalog = authenticated_client.get("/api/crm/connectors/catalog/")
    assert catalog.status_code == 200
    providers = {row["provider"] for row in catalog.data["providers"]}
    assert providers == {"stripe", "onec", "whatsapp", "sms", "telephony"}

    created = authenticated_client.post(
        "/api/crm/connectors/",
        {
            "provider": "sms",
            "name": "Twilio-ish",
            "config": {"webhook_secret": "sec", "from_number": "+1000"},
        },
        format="json",
    )
    assert created.status_code == 201
    assert created.data["webhook_token"]
    assert created.data["config_public"]["webhook_secret"] == "***"
    assert "/api/crm/connectors/webhooks/sms/" in created.data["webhook_path"]


def test_onec_sync_from_pending_documents(authenticated_client, workspace):
    connector = IntegrationConnector.objects.create(
        workspace=workspace,
        provider=IntegrationConnector.Provider.ONEC,
        name="1C main",
        webhook_token="tok-onec",
        config={
            "pending_documents": [
                {
                    "id": "1C-100",
                    "title": "Счёт из 1С",
                    "amount": "2500.00",
                    "doc_type": "invoice",
                }
            ]
        },
    )
    synced = authenticated_client.post(f"/api/crm/connectors/{connector.id}/sync/")
    assert synced.status_code == 200
    assert synced.data["created"] == 1
    assert CrmDocument.objects.filter(workspace=workspace, number="1C-100").exists()
    assert Activity.objects.filter(
        workspace=workspace, channel=Activity.Channel.ONEC
    ).exists()
    connector.refresh_from_db()
    assert connector.config.get("pending_documents") == []


def test_stripe_whatsapp_sms_webhooks(authenticated_client, workspace):
    IntegrationConnector.objects.create(
        workspace=workspace,
        provider=IntegrationConnector.Provider.STRIPE,
        name="Stripe",
        webhook_token="tok-stripe",
        config={"webhook_secret": "s3cret"},
    )
    IntegrationConnector.objects.create(
        workspace=workspace,
        provider=IntegrationConnector.Provider.WHATSAPP,
        name="WA",
        webhook_token="tok-wa",
        config={"verify_token": "verify-me", "webhook_secret": ""},
    )
    sms = IntegrationConnector.objects.create(
        workspace=workspace,
        provider=IntegrationConnector.Provider.SMS,
        name="SMS",
        webhook_token="tok-sms",
        config={},
    )

    bad = authenticated_client.post(
        "/api/crm/connectors/webhooks/stripe/tok-stripe/",
        {"type": "charge.succeeded", "data": {"object": {"id": "ch_1", "amount": 5000}}},
        format="json",
    )
    assert bad.status_code == 403

    ok = authenticated_client.post(
        "/api/crm/connectors/webhooks/stripe/tok-stripe/?secret=s3cret",
        {
            "type": "charge.succeeded",
            "data": {"object": {"id": "ch_1", "amount": 5000}},
        },
        format="json",
    )
    assert ok.status_code == 200
    assert ok.data["created"] == 1
    assert Transaction.objects.filter(workspace=workspace, category="stripe").exists()

    verify = authenticated_client.get(
        "/api/crm/connectors/webhooks/whatsapp/tok-wa/"
        "?hub.mode=subscribe&hub.verify_token=verify-me&hub.challenge=12345"
    )
    assert verify.status_code == 200
    assert verify.content == b"12345"

    wa_msg = authenticated_client.post(
        "/api/crm/connectors/webhooks/whatsapp/tok-wa/",
        {
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "messages": [
                                    {
                                        "id": "wamid.1",
                                        "from": "79001234567",
                                        "text": {"body": "hello"},
                                    }
                                ]
                            }
                        }
                    ]
                }
            ]
        },
        format="json",
    )
    assert wa_msg.status_code == 200
    assert wa_msg.data["created"] == 1
    assert Activity.objects.filter(
        workspace=workspace, channel=Activity.Channel.WHATSAPP, external_id="wa:wamid.1"
    ).exists()

    sms_msg = authenticated_client.post(
        "/api/crm/connectors/webhooks/sms/tok-sms/",
        {"id": "SM1", "from": "+79001112233", "body": "ping"},
        format="json",
    )
    assert sms_msg.status_code == 200
    assert Activity.objects.filter(
        workspace=workspace, channel=Activity.Channel.SMS, external_id="sms:SM1"
    ).exists()

    sent = authenticated_client.post(
        f"/api/crm/connectors/{sms.id}/send/",
        {"to": "+79001112233", "body": "pong"},
        format="json",
    )
    assert sent.status_code == 200
    assert sent.data["sent"] is True
    assert Activity.objects.filter(
        workspace=workspace,
        channel=Activity.Channel.SMS,
        direction=Activity.Direction.OUTBOUND,
    ).exists()


def test_telephony_webhook_and_dial(authenticated_client, workspace):
    tel = IntegrationConnector.objects.create(
        workspace=workspace,
        provider=IntegrationConnector.Provider.TELEPHONY,
        name="PBX",
        webhook_token="tok-tel",
        config={"from_number": "+74951111111"},
    )
    inbound = authenticated_client.post(
        "/api/crm/connectors/webhooks/telephony/tok-tel/",
        {
            "call_id": "c-1",
            "direction": "inbound",
            "from": "+79001112233",
            "to": "+74951111111",
            "status": "answered",
            "duration": 42,
        },
        format="json",
    )
    assert inbound.status_code == 200
    assert inbound.data["created"] == 1
    assert Activity.objects.filter(
        workspace=workspace,
        kind=Activity.Kind.CALL,
        channel=Activity.Channel.TELEPHONY,
        external_id="tel:c-1",
        direction=Activity.Direction.INBOUND,
    ).exists()

    dialed = authenticated_client.post(
        f"/api/crm/connectors/{tel.id}/send/",
        {"to": "+79001112233", "note": "follow-up"},
        format="json",
    )
    assert dialed.status_code == 200
    assert dialed.data["dialed"] is True
    assert Activity.objects.filter(
        workspace=workspace,
        channel=Activity.Channel.TELEPHONY,
        direction=Activity.Direction.OUTBOUND,
    ).exists()


def test_telephony_mango_and_asterisk_dial(authenticated_client, workspace, monkeypatch):
    from crm import connectors as connectors_mod

    mango = IntegrationConnector.objects.create(
        workspace=workspace,
        provider=IntegrationConnector.Provider.TELEPHONY,
        name="Mango",
        webhook_token="tok-mango",
        config={
            "pbx": "mango",
            "api_key": "key1",
            "api_salt": "salt1",
            "extension": "101",
        },
    )
    calls = {}

    def fake_form(url, *, fields, headers=None):
        calls["mango"] = {"url": url, "fields": fields}
        return {"result": 1000}

    monkeypatch.setattr(connectors_mod, "_http_form", fake_form)
    mango_dial = authenticated_client.post(
        f"/api/crm/connectors/{mango.id}/send/",
        {"to": "+79001112233"},
        format="json",
    )
    assert mango_dial.status_code == 200
    assert mango_dial.data["remote"] is True
    assert mango_dial.data["pbx"] == "mango"
    assert "commands/callback" in calls["mango"]["url"]
    assert calls["mango"]["fields"]["vpbx_api_key"] == "key1"
    assert calls["mango"]["fields"]["sign"]

    event = {
        "call_id": "m-99",
        "call_state": "Connected",
        "from": {"number": "79001112233"},
        "to": {"extension": "101"},
        "location": "abonent",
    }
    raw_json = json.dumps(event, ensure_ascii=False, separators=(",", ":"))
    sign = hashlib.sha256(f"key1{raw_json}salt1".encode()).hexdigest()
    mango_event = authenticated_client.post(
        "/api/crm/connectors/webhooks/telephony/tok-mango/",
        {"vpbx_api_key": "key1", "json": raw_json, "sign": sign},
        format="json",
    )
    assert mango_event.status_code == 200
    assert Activity.objects.filter(external_id="tel:m-99").exists()

    ari = IntegrationConnector.objects.create(
        workspace=workspace,
        provider=IntegrationConnector.Provider.TELEPHONY,
        name="Asterisk",
        webhook_token="tok-ari",
        config={
            "pbx": "asterisk",
            "ari_base_url": "http://pbx.local:8088/ari",
            "ari_user": "ari",
            "ari_password": "secret",
            "endpoint": "PJSIP/100",
            "context": "from-internal",
        },
    )

    def fake_json(url, *, headers=None, data=None, method=None):
        calls["ari"] = {"url": url, "headers": headers, "method": method}
        return {"id": "chan-1"}

    monkeypatch.setattr(connectors_mod, "_http_json", fake_json)
    ari_dial = authenticated_client.post(
        f"/api/crm/connectors/{ari.id}/send/",
        {"to": "79005554433"},
        format="json",
    )
    assert ari_dial.status_code == 200
    assert ari_dial.data["pbx"] == "asterisk"
    assert ari_dial.data["channel_id"] == "chan-1"
    assert "/channels?" in calls["ari"]["url"]
    assert "endpoint=PJSIP%2F100" in calls["ari"]["url"]
    assert calls["ari"]["headers"]["Authorization"].startswith("Basic ")

    cdr = authenticated_client.post(
        "/api/crm/connectors/webhooks/telephony/tok-ari/",
        {
            "uniqueid": "1730000.1",
            "src": "100",
            "dst": "79005554433",
            "disposition": "ANSWERED",
            "billsec": 12,
            "direction": "outbound",
        },
        format="json",
    )
    assert cdr.status_code == 200
    assert Activity.objects.filter(external_id="tel:1730000.1").exists()


def test_asterisk_ari_and_ami_event_ingest(authenticated_client, workspace):
    IntegrationConnector.objects.create(
        workspace=workspace,
        provider=IntegrationConnector.Provider.TELEPHONY,
        name="Asterisk events",
        webhook_token="tok-ari-ev",
        config={"pbx": "asterisk"},
    )
    ari = authenticated_client.post(
        "/api/crm/connectors/webhooks/telephony/tok-ari-ev/",
        {
            "type": "ChannelStateChange",
            "channel": {
                "id": "1731111.5",
                "name": "PJSIP/trunk-00000001",
                "state": "Up",
                "caller": {"number": "79001112233"},
                "connected": {"number": "100"},
                "dialplan": {"context": "from-trunk", "exten": "100"},
            },
        },
        format="json",
    )
    assert ari.status_code == 200
    assert ari.data["created"] == 1
    assert ari.data["source"] == "ari"
    assert Activity.objects.filter(
        workspace=workspace,
        external_id="tel:1731111.5",
        direction=Activity.Direction.INBOUND,
    ).exists()

    noise = authenticated_client.post(
        "/api/crm/connectors/webhooks/telephony/tok-ari-ev/",
        {"type": "ChannelVarset", "channel": {"id": "x"}},
        format="json",
    )
    assert noise.status_code == 200
    assert noise.data["created"] == 0

    ami = authenticated_client.post(
        "/api/crm/connectors/webhooks/telephony/tok-ari-ev/",
        {
            "events": [
                {
                    "Event": "Hangup",
                    "Uniqueid": "1732222.9",
                    "CallerIDNum": "100",
                    "ConnectedLineNum": "79005554433",
                    "Context": "from-internal",
                    "Cause-txt": "Normal Clearing",
                    "BillableSeconds": "15",
                }
            ]
        },
        format="json",
    )
    assert ami.status_code == 200
    assert ami.data["created"] == 1
    assert Activity.objects.filter(
        workspace=workspace,
        external_id="tel:1732222.9",
        direction=Activity.Direction.OUTBOUND,
    ).exists()


def test_click_to_call_links_person_and_deal(authenticated_client, workspace, user):
    from crm.models import Deal, Organization, Person
    from crm.services import ensure_default_pipeline

    person = Person.objects.create(
        workspace=workspace, full_name="Alice", phone="+79001112233", owner=user
    )
    org = Organization.objects.create(workspace=workspace, name="Acme")
    pipeline = ensure_default_pipeline(workspace)
    deal = Deal.objects.create(
        workspace=workspace,
        pipeline=pipeline,
        stage=pipeline.stages.first(),
        title="Deal call",
        organization=org,
        person=person,
        owner=user,
    )
    tel = IntegrationConnector.objects.create(
        workspace=workspace,
        provider=IntegrationConnector.Provider.TELEPHONY,
        name="PBX",
        webhook_token="tok-ctc",
        config={"pbx": "generic"},
    )
    dialed = authenticated_client.post(
        f"/api/crm/connectors/{tel.id}/send/",
        {
            "to": "+79001112233",
            "note": "from deal",
            "person_id": person.id,
            "deal_id": deal.id,
        },
        format="json",
    )
    assert dialed.status_code == 200
    activity = Activity.objects.get(
        workspace=workspace,
        channel=Activity.Channel.TELEPHONY,
        direction=Activity.Direction.OUTBOUND,
        person=person,
        deal=deal,
    )
    assert "from deal" in activity.body

    board = authenticated_client.get("/api/crm/deals/")
    assert board.status_code == 200
    row = next(d for d in board.data if d["id"] == deal.id)
    assert row["person_phone"] == "+79001112233"


def test_mango_webhook_sign_verification(authenticated_client, workspace):
    api_key = "key1"
    api_salt = "salt1"
    IntegrationConnector.objects.create(
        workspace=workspace,
        provider=IntegrationConnector.Provider.TELEPHONY,
        name="Mango signed",
        webhook_token="tok-mango-sign",
        config={"pbx": "mango", "api_key": api_key, "api_salt": api_salt, "extension": "101"},
    )
    event = {
        "call_id": "signed-1",
        "call_state": "Connected",
        "from": {"number": "79001112233"},
        "to": {"extension": "101"},
    }
    raw_json = json.dumps(event, ensure_ascii=False, separators=(",", ":"))
    sign = hashlib.sha256(f"{api_key}{raw_json}{api_salt}".encode()).hexdigest()

    bad = authenticated_client.post(
        "/api/crm/connectors/webhooks/telephony/tok-mango-sign/",
        {"vpbx_api_key": api_key, "json": raw_json, "sign": "deadbeef"},
        format="json",
    )
    assert bad.status_code == 403

    ok = authenticated_client.post(
        "/api/crm/connectors/webhooks/telephony/tok-mango-sign/",
        {"vpbx_api_key": api_key, "json": raw_json, "sign": sign},
        format="json",
    )
    assert ok.status_code == 200
    assert ok.data["created"] == 1
    assert Activity.objects.filter(
        workspace=workspace,
        external_id="tel:signed-1",
        direction=Activity.Direction.INBOUND,
    ).exists()
