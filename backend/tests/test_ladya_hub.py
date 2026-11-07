import hashlib

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from ladya.defaults import get_or_create_ladya_settings
from ladya.models import Laboratory, Package
from ladya.services import PACKAGE_TRANSITIONS, assert_package_transition
from rest_framework.exceptions import ValidationError
from workspaces.models import WorkspaceMember


@pytest.fixture
def enable_ladya(workspace):
    row, _ = get_or_create_ladya_settings(workspace)
    row.ladya_hub_enabled = True
    row.save(update_fields=["ladya_hub_enabled", "updated_at"])
    return row


def test_settings_flag_gates_api(authenticated_client, workspace, enable_ladya):
    row, _ = get_or_create_ladya_settings(workspace)
    row.ladya_hub_enabled = False
    row.save(update_fields=["ladya_hub_enabled", "updated_at"])

    denied = authenticated_client.get("/api/ladya/laboratories/")
    assert denied.status_code == 403

    ok = authenticated_client.patch(
        "/api/ladya/settings/",
        {"ladya_hub_enabled": True},
        format="json",
    )
    assert ok.status_code == 200
    assert ok.data["ladya_hub_enabled"] is True

    listed = authenticated_client.get("/api/ladya/laboratories/")
    assert listed.status_code == 200
    assert listed.data == []


def test_laboratory_crud(authenticated_client, enable_ladya):
    created = authenticated_client.post(
        "/api/ladya/laboratories/",
        {
            "slug": "central",
            "title": "Центральный ЛАД",
            "kind": "central_lad",
        },
        format="json",
    )
    assert created.status_code == 201
    lab_id = created.data["id"]

    patched = authenticated_client.patch(
        f"/api/ladya/laboratories/{lab_id}/",
        {"title": "ЛАД Hub"},
        format="json",
    )
    assert patched.status_code == 200
    assert patched.data["title"] == "ЛАД Hub"


def test_package_status_transitions_and_file_sha256(
    authenticated_client, workspace, enable_ladya
):
    lab_a = Laboratory.objects.create(
        workspace=workspace,
        slug="lab-a",
        title="Lab A",
        kind=Laboratory.Kind.PRIVATE_LAB,
    )
    lab_b = Laboratory.objects.create(
        workspace=workspace,
        slug="lab-b",
        title="Lab B",
        kind=Laboratory.Kind.PRIVATE_LAB,
    )

    created = authenticated_client.post(
        "/api/ladya/packages/",
        {
            "title": "Пакет 1",
            "summary": "описание",
            "from_laboratory": lab_a.id,
            "to_laboratory": lab_b.id,
        },
        format="json",
    )
    assert created.status_code == 201
    package_id = created.data["id"]
    assert created.data["display_code"] == "PKG-1"
    assert created.data["status"] == "draft"

    bad = authenticated_client.post(
        f"/api/ladya/packages/{package_id}/transition/",
        {"status": "closed"},
        format="json",
    )
    assert bad.status_code == 400

    submitted = authenticated_client.post(
        f"/api/ladya/packages/{package_id}/transition/",
        {"status": "submitted", "reason": "на рассмотрение"},
        format="json",
    )
    assert submitted.status_code == 200
    assert submitted.data["status"] == "submitted"

    accepted = authenticated_client.post(
        f"/api/ladya/packages/{package_id}/transition/",
        {"status": "accepted"},
        format="json",
    )
    assert accepted.status_code == 200
    assert accepted.data["status"] == "accepted"

    content = b"ladya-package-bytes"
    expected = hashlib.sha256(content).hexdigest()
    upload = SimpleUploadedFile("note.txt", content, content_type="text/plain")
    uploaded = authenticated_client.post(
        f"/api/ladya/packages/{package_id}/files/",
        {"file": upload},
        format="multipart",
    )
    assert uploaded.status_code == 201
    assert uploaded.data["sha256"] == expected
    assert uploaded.data["original_name"] == "note.txt"
    assert uploaded.data["size"] == len(content)

    closed = authenticated_client.post(
        f"/api/ladya/packages/{package_id}/transition/",
        {"status": "in_progress"},
        format="json",
    )
    assert closed.status_code == 200
    done = authenticated_client.post(
        f"/api/ladya/packages/{package_id}/transition/",
        {"status": "closed"},
        format="json",
    )
    assert done.status_code == 200
    assert done.data["status"] == "closed"
    assert len(done.data["status_events"]) >= 4


def test_intake_convert_to_package(authenticated_client, workspace, enable_ladya):
    lab = Laboratory.objects.create(
        workspace=workspace,
        slug="central",
        title="Центральный",
        kind=Laboratory.Kind.CENTRAL_LAD,
    )
    created = authenticated_client.post(
        "/api/ladya/intake/",
        {
            "body": "Нужна помощь с методологией",
            "contact": "@fedosov",
            "source": "web_form",
        },
        format="json",
    )
    assert created.status_code == 201
    intake_id = created.data["id"]
    assert created.data["status"] == "new"

    converted = authenticated_client.post(
        f"/api/ladya/intake/{intake_id}/convert/",
        {
            "title": "Из intake",
            "to_laboratory": lab.id,
        },
        format="json",
    )
    assert converted.status_code == 201
    assert converted.data["intake"]["status"] == "converted"
    assert converted.data["package"]["title"] == "Из intake"
    assert converted.data["package"]["to_laboratory"] == lab.id
    assert Package.objects.filter(workspace=workspace).count() == 1


def test_workspace_isolation(authenticated_client, workspace, enable_ladya, other_user):
    Laboratory.objects.create(
        workspace=workspace,
        slug="only-here",
        title="Only",
        kind=Laboratory.Kind.LAB0,
    )
    other_ws = other_user.workspace_memberships.first().workspace
    row, _ = get_or_create_ladya_settings(other_ws)
    row.ladya_hub_enabled = True
    row.save(update_fields=["ladya_hub_enabled", "updated_at"])

    other_client = APIClient()
    other_client.force_authenticate(user=other_user)
    other_client.credentials(HTTP_X_WORKSPACE_ID=str(other_ws.id))
    listed = other_client.get("/api/ladya/laboratories/")
    assert listed.status_code == 200
    assert listed.data == []


def test_package_transition_matrix_unit():
    assert_package_transition("draft", "submitted")
    with pytest.raises(ValidationError):
        assert_package_transition("draft", "closed")
    assert "accepted" in PACKAGE_TRANSITIONS["submitted"]


def test_package_link_delivery_task(authenticated_client, workspace, user, enable_ladya):
    from delivery.models import DeliveryTask

    task = DeliveryTask.objects.create(
        workspace=workspace,
        title="Agent task for package",
        created_by=user,
        status=DeliveryTask.Status.DRAFT,
    )
    created = authenticated_client.post(
        "/api/ladya/packages/",
        {"title": "Связанный пакет"},
        format="json",
    )
    assert created.status_code == 201
    package_id = created.data["id"]

    linked = authenticated_client.patch(
        f"/api/ladya/packages/{package_id}/",
        {"linked_delivery_task": task.id},
        format="json",
    )
    assert linked.status_code == 200
    assert linked.data["linked_delivery_task"] == task.id

    unlinked = authenticated_client.patch(
        f"/api/ladya/packages/{package_id}/",
        {"linked_delivery_task": None},
        format="json",
    )
    assert unlinked.status_code == 200
    assert unlinked.data["linked_delivery_task"] is None


def test_viewer_can_create_intake_but_not_lab(
    api_client, workspace, enable_ladya, other_user
):
    WorkspaceMember.objects.create(
        workspace=workspace,
        user=other_user,
        role=WorkspaceMember.Role.VIEWER,
    )
    client = APIClient()
    client.force_authenticate(user=other_user)
    client.credentials(HTTP_X_WORKSPACE_ID=str(workspace.id))

    denied = client.post(
        "/api/ladya/laboratories/",
        {"slug": "x", "title": "X", "kind": "lab0"},
        format="json",
    )
    assert denied.status_code == 403

    intake = client.post(
        "/api/ladya/intake/",
        {"body": "viewer intake", "contact": "v@example.com"},
        format="json",
    )
    assert intake.status_code == 201
