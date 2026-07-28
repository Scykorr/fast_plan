"""CRM polish for v0.15: act PDF, IG/VK activity, saved filters, report builder, GraphQL."""

import pytest
from django.utils import timezone
from rest_framework import status

from crm.channels import ingest_instagram_webhook, ingest_vk_callback
from crm.commerce_pdf import render_crm_document_pdf
from crm.models import Activity, ChannelConnection, CrmDocument, Organization, Person


@pytest.mark.django_db
def test_act_document_pdf(authenticated_client, workspace):
    org = Organization.objects.create(workspace=workspace, name="Acme Act")
    created = authenticated_client.post(
        "/api/crm/documents/",
        {
            "doc_type": "act",
            "title": "Акт 1",
            "number": "ACT-1",
            "amount": "500.00",
            "status": "sent",
            "organization_id": org.id,
            "body": "Работы выполнены",
            "line_items": [{"title": "Dev", "qty": 1, "price": 500}],
        },
        format="json",
    )
    assert created.status_code == status.HTTP_201_CREATED
    doc_id = created.data["id"]

    pdf = authenticated_client.post(f"/api/crm/documents/{doc_id}/pdf/", {}, format="json")
    assert pdf.status_code == status.HTTP_200_OK
    assert pdf.data["pdf_url"]

    doc = CrmDocument.objects.get(pk=doc_id)
    assert doc.doc_type == CrmDocument.DocType.ACT
    raw = render_crm_document_pdf(doc)
    assert raw[:4] == b"%PDF"


@pytest.mark.django_db
def test_instagram_and_vk_activity_ingest(authenticated_client, workspace):
    person = Person.objects.create(
        workspace=workspace,
        full_name="Social User",
        social_urls=["https://instagram.com/bob"],
    )
    ig = ChannelConnection.objects.create(
        workspace=workspace,
        provider=ChannelConnection.Provider.INSTAGRAM,
        name="IG",
        config={"verify_token": "verify-ig", "webhook_secret": "ig-sec"},
    )
    created = ingest_instagram_webhook(
        ig,
        {
            "entry": [
                {
                    "messaging": [
                        {
                            "sender": {"id": "bob"},
                            "message": {"mid": "m1", "text": "hi from ig"},
                        }
                    ]
                }
            ]
        },
    )
    assert created == 1
    assert Activity.objects.filter(
        workspace=workspace, kind=Activity.Kind.INSTAGRAM, external_id="ig:m1"
    ).exists()

    hook = authenticated_client.post(
        "/api/crm/channels/instagram/ig-sec/",
        {
            "entry": [
                {
                    "messaging": [
                        {
                            "sender": {"id": "bob"},
                            "message": {"mid": "m2", "text": "again"},
                        }
                    ]
                }
            ]
        },
        format="json",
    )
    assert hook.status_code == status.HTTP_200_OK
    assert hook.data["created"] == 1

    verify = authenticated_client.get(
        "/api/crm/channels/instagram/ig-sec/",
        {
            "hub.mode": "subscribe",
            "hub.verify_token": "verify-ig",
            "hub.challenge": "12345",
        },
    )
    assert verify.status_code == status.HTTP_200_OK
    assert verify.content == b"12345"

    vk = ChannelConnection.objects.create(
        workspace=workspace,
        provider=ChannelConnection.Provider.VK,
        name="VK",
        config={
            "confirmation_code": "conf-ok",
            "secret": "vk-secret",
            "webhook_secret": "vk-path",
        },
    )
    conf, n = ingest_vk_callback(vk, {"type": "confirmation"})
    assert conf == "conf-ok"
    assert n == 0

    _, n2 = ingest_vk_callback(
        vk,
        {
            "type": "message_new",
            "secret": "vk-secret",
            "object": {
                "message": {
                    "id": 42,
                    "from_id": 7,
                    "text": "vk hello",
                    "date": int(timezone.now().timestamp()),
                }
            },
        },
    )
    assert n2 == 1
    assert Activity.objects.filter(
        workspace=workspace, kind=Activity.Kind.VK, external_id="vk:42"
    ).exists()
    _ = person

    vk_hook = authenticated_client.post(
        "/api/crm/channels/vk/vk-path/",
        {"type": "confirmation"},
        format="json",
    )
    assert vk_hook.status_code == status.HTTP_200_OK
    assert vk_hook.content == b"conf-ok"


@pytest.mark.django_db
def test_saved_filters_crud(authenticated_client, workspace):
    created = authenticated_client.post(
        "/api/crm/saved-filters/",
        {
            "target": "leads",
            "name": "Open leads",
            "params": {"q": "acme", "status": "new"},
        },
        format="json",
    )
    assert created.status_code == status.HTTP_201_CREATED
    fid = created.data["id"]

    listed = authenticated_client.get("/api/crm/saved-filters/?target=leads")
    assert listed.status_code == status.HTTP_200_OK
    assert any(row["id"] == fid for row in listed.data)

    deleted = authenticated_client.delete(f"/api/crm/saved-filters/{fid}/")
    assert deleted.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.django_db
def test_report_builder_and_graphql(authenticated_client, workspace):
    run = authenticated_client.post(
        "/api/crm/reports/run/",
        {"query": {"metric": "conversion", "filters": {}}},
        format="json",
    )
    assert run.status_code == status.HTTP_200_OK
    assert run.data["metric"] == "conversion"
    assert "conversion_rate" in run.data

    csv_run = authenticated_client.post(
        "/api/crm/reports/run/",
        {"query": {"metric": "by_owner"}, "format": "csv"},
        format="json",
    )
    assert csv_run.status_code == status.HTTP_200_OK
    assert "text/csv" in csv_run["Content-Type"]

    gql = authenticated_client.post(
        "/api/crm/graphql/",
        {"query": "{ organizations { id name } deals { id title } }"},
        format="json",
    )
    assert gql.status_code == status.HTTP_200_OK
    assert "data" in gql.data
    assert "organizations" in gql.data["data"]
