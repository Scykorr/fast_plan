"""P6g/h/i: omnichannel, commerce docs, CRM analytics."""

from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework import status

from crm.channels import ingest_activity, ingest_telegram_webhook
from crm.commerce_pdf import render_crm_document_pdf
from crm.models import (
    Activity,
    ChannelConnection,
    CrmDocument,
    Deal,
    Lead,
    Organization,
    Person,
)
from crm.services import ensure_default_pipeline


@pytest.mark.django_db
def test_omnichannel_activity_ingest_and_telegram_webhook(authenticated_client, workspace):
    person = Person.objects.create(
        workspace=workspace, full_name="TG User", telegram="alice", email="a@ex.test"
    )
    created = ingest_activity(
        workspace,
        kind=Activity.Kind.EMAIL,
        channel=Activity.Channel.EMAIL,
        direction=Activity.Direction.INBOUND,
        external_id="msg-1",
        subject="Hello",
        body="Body",
        occurred_at=timezone.now(),
        person=person,
    )
    assert created is not None
    assert Activity.objects.filter(external_id="msg-1").count() == 1
    # dedupe
    assert (
        ingest_activity(
            workspace,
            kind=Activity.Kind.EMAIL,
            channel=Activity.Channel.EMAIL,
            direction=Activity.Direction.INBOUND,
            external_id="msg-1",
            subject="Hello",
            body="Body",
            occurred_at=timezone.now(),
            person=person,
        )
        is None
    )

    connection = ChannelConnection.objects.create(
        workspace=workspace,
        provider=ChannelConnection.Provider.TELEGRAM,
        name="Bot",
        config={"bot_token": "x", "webhook_secret": "sec123"},
    )
    activity = ingest_telegram_webhook(
        connection,
        {
            "message": {
                "message_id": 9,
                "date": int(timezone.now().timestamp()),
                "text": "ping",
                "chat": {"id": 1},
                "from": {"username": "alice", "first_name": "A"},
            }
        },
    )
    assert activity is not None
    assert activity.kind == Activity.Kind.TELEGRAM
    assert activity.person_id == person.id

    hook = authenticated_client.post(
        "/api/crm/channels/telegram/sec123/",
        {
            "message": {
                "message_id": 10,
                "date": int(timezone.now().timestamp()),
                "text": "pong",
                "chat": {"id": 1},
                "from": {"username": "alice"},
            }
        },
        format="json",
    )
    # webhook is AllowAny — client still works
    assert hook.status_code == status.HTTP_200_OK

    listed = authenticated_client.get("/api/crm/channels/")
    assert listed.status_code == status.HTTP_200_OK
    assert len(listed.data) >= 1


@pytest.mark.django_db
def test_commerce_document_pdf_payment_and_arap(authenticated_client, workspace, user):
    org = Organization.objects.create(workspace=workspace, name="Acme")
    created = authenticated_client.post(
        "/api/crm/documents/",
        {
            "doc_type": "invoice",
            "title": "Invoice 1",
            "number": "INV-1",
            "amount": "1000.00",
            "status": "sent",
            "organization_id": org.id,
            "line_items": [{"title": "Work", "qty": 1, "price": 1000}],
        },
        format="json",
    )
    assert created.status_code == status.HTTP_201_CREATED
    doc_id = created.data["id"]

    pdf = authenticated_client.post(f"/api/crm/documents/{doc_id}/pdf/", {}, format="json")
    assert pdf.status_code == status.HTTP_200_OK
    assert pdf.data["pdf_url"]

    doc = CrmDocument.objects.get(pk=doc_id)
    raw = render_crm_document_pdf(doc)
    assert raw[:4] == b"%PDF"

    pay = authenticated_client.post(
        f"/api/crm/documents/{doc_id}/payments/",
        {"amount": "1000.00", "paid_at": timezone.localdate().isoformat()},
        format="json",
    )
    assert pay.status_code == status.HTTP_201_CREATED
    doc.refresh_from_db()
    assert doc.status == CrmDocument.Status.PAID

    ar = authenticated_client.get("/api/crm/ar-ap/")
    assert ar.status_code == status.HTTP_200_OK
    assert "ar_open_amount" in ar.data


@pytest.mark.django_db
def test_crm_analytics_dashboard(authenticated_client, workspace, user):
    pipeline = ensure_default_pipeline(workspace)
    won = pipeline.stages.filter(is_won=True).first()
    open_stage = pipeline.stages.exclude(is_won=True).exclude(is_lost=True).first()
    Lead.objects.create(
        workspace=workspace,
        full_name="L1",
        email="l1@ex.test",
        source="website",
        status=Lead.Status.CONVERTED,
    )
    Lead.objects.create(
        workspace=workspace,
        full_name="L2",
        email="l2@ex.test",
        source="website",
        status=Lead.Status.NEW,
    )
    Deal.objects.create(
        workspace=workspace,
        pipeline=pipeline,
        stage=won,
        title="Won",
        amount=Decimal("5000"),
        probability=100,
        owner=user,
    )
    Deal.objects.create(
        workspace=workspace,
        pipeline=pipeline,
        stage=open_stage,
        title="Open",
        amount=Decimal("2000"),
        probability=50,
        owner=user,
    )

    resp = authenticated_client.get("/api/crm/analytics/")
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["leads"]["total"] >= 2
    assert resp.data["leads"]["conversion_rate"] > 0
    assert resp.data["deals"]["won_count"] >= 1
    assert resp.data["deals"]["avg_check"] > 0
    assert any(row["owner_id"] == user.id for row in resp.data["deals"]["by_owner"])

    saved = authenticated_client.post(
        "/api/crm/saved-reports/",
        {"name": "Weekly", "query": {"metric": "conversion"}},
        format="json",
    )
    assert saved.status_code == status.HTTP_201_CREATED
