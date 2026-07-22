"""P6b CRM client card API tests."""

from datetime import timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework import status

from crm.models import Activity, Organization, Person, Tag
from workspaces.models import WorkspaceMember


@pytest.mark.django_db
def test_person_messengers_tags_owner_and_stale(
    authenticated_client, workspace, user
):
    tag = Tag.objects.create(workspace=workspace, name="vip", color="#22c55e")
    person = authenticated_client.post(
        "/api/crm/people/",
        {
            "full_name": "Ada Lovelace",
            "telegram": "@ada",
            "whatsapp": "+10001112233",
            "social_urls": ["https://linkedin.com/in/ada"],
            "owner_id": user.id,
            "tag_ids": [tag.id],
        },
        format="json",
    )
    assert person.status_code == status.HTTP_201_CREATED
    assert person.data["telegram"] == "@ada"
    assert person.data["whatsapp"] == "+10001112233"
    assert person.data["social_urls"] == ["https://linkedin.com/in/ada"]
    assert person.data["owner_id"] == user.id
    assert person.data["tags"][0]["name"] == "vip"
    assert person.data["days_since_touch"] is None

    stale = authenticated_client.get("/api/crm/people/?stale_days=14")
    assert stale.status_code == status.HTTP_200_OK
    assert any(row["id"] == person.data["id"] for row in stale.data)

    Activity.objects.create(
        workspace=workspace,
        kind=Activity.Kind.CALL,
        subject="Check-in",
        occurred_at=timezone.now(),
        person_id=person.data["id"],
        created_by=user,
    )
    fresh = authenticated_client.get("/api/crm/people/?stale_days=14")
    assert fresh.status_code == status.HTTP_200_OK
    assert all(row["id"] != person.data["id"] for row in fresh.data)


@pytest.mark.django_db
def test_activity_invoice_order_kinds(authenticated_client, workspace, user):
    org = Organization.objects.create(workspace=workspace, name="Acme")
    invoice = authenticated_client.post(
        "/api/crm/activities/",
        {
            "kind": "invoice",
            "subject": "INV-1",
            "organization_id": org.id,
        },
        format="json",
    )
    assert invoice.status_code == status.HTTP_201_CREATED
    assert invoice.data["kind"] == "invoice"

    order = authenticated_client.post(
        "/api/crm/activities/",
        {
            "kind": "order",
            "subject": "ORD-1",
            "organization_id": org.id,
        },
        format="json",
    )
    assert order.status_code == status.HTTP_201_CREATED
    assert order.data["kind"] == "order"


@pytest.mark.django_db
def test_comments_and_attachments(authenticated_client, workspace, user):
    person = Person.objects.create(workspace=workspace, full_name="Bob")
    comment = authenticated_client.post(
        "/api/crm/comments/",
        {"body": "Follow up next week", "person_id": person.id},
        format="json",
    )
    assert comment.status_code == status.HTTP_201_CREATED
    assert comment.data["body"] == "Follow up next week"

    listed = authenticated_client.get(f"/api/crm/comments/?person_id={person.id}")
    assert listed.status_code == status.HTTP_200_OK
    assert len(listed.data) == 1

    upload = SimpleUploadedFile(
        "brief.pdf",
        b"%PDF-1.4 fake",
        content_type="application/pdf",
    )
    attachment = authenticated_client.post(
        "/api/crm/attachments/",
        {"file": upload, "person_id": person.id},
        format="multipart",
    )
    assert attachment.status_code == status.HTTP_201_CREATED
    assert attachment.data["name"] == "brief.pdf"
    assert attachment.data["url"]

    files = authenticated_client.get(f"/api/crm/attachments/?person_id={person.id}")
    assert files.status_code == status.HTTP_200_OK
    assert len(files.data) == 1


@pytest.mark.django_db
def test_segment_rule_stale_and_tag(authenticated_client, workspace, user):
    tag = Tag.objects.create(workspace=workspace, name="hot")
    person = Person.objects.create(workspace=workspace, full_name="Carol")
    authenticated_client.post(
        f"/api/crm/people/{person.id}/tags/",
        {"tag_id": tag.id},
        format="json",
    )
    Activity.objects.create(
        workspace=workspace,
        kind=Activity.Kind.NOTE,
        subject="Old note",
        occurred_at=timezone.now() - timedelta(days=30),
        person=person,
        created_by=user,
    )

    segment = authenticated_client.post(
        "/api/crm/segments/",
        {
            "name": "Hot stale",
            "kind": "rule",
            "rule": {"tag": "hot", "stale_days": 14},
        },
        format="json",
    )
    assert segment.status_code == status.HTTP_201_CREATED
    assert segment.data["people_count"] == 1

    members = authenticated_client.get(
        f"/api/crm/segments/{segment.data['id']}/members/"
    )
    assert members.status_code == status.HTTP_200_OK
    assert members.data["people"][0]["full_name"] == "Carol"

    filtered = authenticated_client.get(
        f"/api/crm/people/?segment_id={segment.data['id']}"
    )
    assert filtered.status_code == status.HTTP_200_OK
    assert len(filtered.data) == 1


@pytest.mark.django_db
def test_workspace_crm_role(authenticated_client, workspace, user):
    membership = WorkspaceMember.objects.get(workspace=workspace, user=user)
    patched = authenticated_client.patch(
        f"/api/workspace/members/{membership.id}/",
        {"crm_role": "sales_lead"},
        format="json",
    )
    assert patched.status_code == status.HTTP_200_OK
    assert patched.data["crm_role"] == "sales_lead"

    listed = authenticated_client.get("/api/workspace/members/")
    assert listed.status_code == status.HTTP_200_OK
    row = next(m for m in listed.data if m["id"] == membership.id)
    assert row["crm_role"] == "sales_lead"
