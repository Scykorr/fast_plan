"""CRM custom fields + Beeline/MTS telephony polish."""

import pytest
from rest_framework import status

from crm.connectors import normalize_telephony_payload
from crm.models import CrmCustomFieldDefinition, Organization, Person


@pytest.mark.django_db
def test_custom_fields_definition_and_entity_values(authenticated_client, workspace):
    person = Person.objects.create(workspace=workspace, full_name="CF User")
    created = authenticated_client.post(
        "/api/crm/custom-fields/",
        {
            "target": "person",
            "key": "vip",
            "label": "VIP",
            "field_type": "bool",
        },
        format="json",
    )
    assert created.status_code == status.HTTP_201_CREATED
    assert created.data["key"] == "vip"

    listed = authenticated_client.get("/api/crm/custom-fields/?target=person")
    assert listed.status_code == status.HTTP_200_OK
    assert any(row["key"] == "vip" for row in listed.data)

    put = authenticated_client.put(
        f"/api/crm/person/{person.id}/custom-fields/",
        {"values": {"vip": True}},
        format="json",
    )
    assert put.status_code == status.HTTP_200_OK
    assert put.data["values"]["vip"] is True

    got = authenticated_client.get(f"/api/crm/person/{person.id}/custom-fields/")
    assert got.status_code == status.HTTP_200_OK
    assert got.data["values"]["vip"] is True
    assert any(d["key"] == "vip" for d in got.data["definitions"])

    org = Organization.objects.create(workspace=workspace, name="CF Org")
    authenticated_client.post(
        "/api/crm/custom-fields/",
        {
            "target": "organization",
            "key": "tier",
            "label": "Tier",
            "field_type": "select",
            "options": ["A", "B"],
        },
        format="json",
    )
    org_put = authenticated_client.put(
        f"/api/crm/organization/{org.id}/custom-fields/",
        {"values": {"tier": "A"}},
        format="json",
    )
    assert org_put.status_code == status.HTTP_200_OK
    assert org_put.data["values"]["tier"] == "A"
    assert CrmCustomFieldDefinition.objects.filter(workspace=workspace).count() >= 2


@pytest.mark.django_db
def test_openapi_schema_available(authenticated_client):
    res = authenticated_client.get("/api/schema/")
    assert res.status_code == status.HTTP_200_OK
    body = res.content.decode("utf-8")
    assert "openapi" in body.lower() or "paths" in body


def test_beeline_and_mts_payload_normalize():
    bee = normalize_telephony_payload(
        {
            "pbx": "beeline",
            "beeline_call_id": "b-1",
            "ani": "+79001112233",
            "dnis": "100",
            "direction": "inbound",
            "recordingUrl": "https://example.com/rec.wav",
        }
    )
    assert bee["source"] == "beeline"
    assert bee["call_id"] == "b-1"
    assert bee["recording_url"].endswith(".wav")

    mts = normalize_telephony_payload(
        {
            "carrier": "mts",
            "mts_call_id": "m-9",
            "caller": "79005556677",
            "callee": "200",
            "duration": 42,
        }
    )
    assert mts["source"] == "mts"
    assert mts["call_id"] == "m-9"
    assert mts["duration"] == 42
