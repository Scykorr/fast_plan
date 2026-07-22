"""P6d CRM leads API tests."""

import io

import pytest
from rest_framework import status

from crm.models import Lead
from crm.services import compute_lead_score
from workspaces.models import WorkspaceMember


@pytest.mark.django_db
def test_lead_score_dedupe_assign_convert(authenticated_client, workspace, user):
    assert compute_lead_score(
        email="a@b.test", phone="+1", company_name="Acme", source="referral"
    ) == 75

    created = authenticated_client.post(
        "/api/crm/leads/",
        {
            "full_name": "Nina Volkov",
            "email": "nina@acme.test",
            "phone": "+79991112233",
            "company_name": "Acme",
            "source": "website",
            "assign": "round_robin",
        },
        format="json",
    )
    assert created.status_code == status.HTTP_201_CREATED
    assert created.data["score"] >= 40
    assert created.data["assigned_to"] == user.id
    lead_id = created.data["id"]

    conflict = authenticated_client.post(
        "/api/crm/leads/",
        {
            "full_name": "Nina Dup",
            "email": "nina@acme.test",
        },
        format="json",
    )
    assert conflict.status_code == status.HTTP_409_CONFLICT
    assert conflict.data["duplicates"]

    forced = authenticated_client.post(
        "/api/crm/leads/",
        {
            "full_name": "Nina Forced",
            "email": "nina@acme.test",
            "force": True,
        },
        format="json",
    )
    assert forced.status_code == status.HTTP_201_CREATED

    assigned = authenticated_client.post(
        f"/api/crm/leads/{lead_id}/assign/",
        {"mode": "round_robin"},
        format="json",
    )
    assert assigned.status_code == status.HTTP_200_OK
    assert assigned.data["assigned_to"] == user.id

    converted = authenticated_client.post(
        f"/api/crm/leads/{lead_id}/convert/",
        {"amount": "12000"},
        format="json",
    )
    assert converted.status_code == status.HTTP_201_CREATED
    assert converted.data["lead"]["status"] == "converted"
    assert converted.data["deal"]["title"]
    assert float(converted.data["deal"]["amount"]) == 12000.0
    assert Lead.objects.get(pk=lead_id).deal_id == converted.data["deal"]["id"]


@pytest.mark.django_db
def test_lead_csv_import_round_robin(authenticated_client, workspace, user):
    WorkspaceMember.objects.filter(workspace=workspace, user=user).update(
        crm_role="sales"
    )
    csv_body = (
        "name,email,phone,company,source\n"
        "Alice,alice@ex.test,+111,CoA,form\n"
        "Bob,bob@ex.test,+222,CoB,ads\n"
    )
    upload = io.BytesIO(csv_body.encode("utf-8"))
    upload.name = "leads.csv"
    imported = authenticated_client.post(
        "/api/crm/leads/import/",
        {"file": upload, "assign": "round_robin"},
        format="multipart",
    )
    assert imported.status_code == status.HTTP_200_OK
    assert imported.data["created"] == 2
    assert Lead.objects.filter(workspace=workspace).count() == 2
    assert Lead.objects.filter(assigned_to=user).count() == 2

    listed = authenticated_client.get("/api/crm/leads/?q=Alice")
    assert listed.status_code == status.HTTP_200_OK
    assert listed.data[0]["full_name"] == "Alice"
