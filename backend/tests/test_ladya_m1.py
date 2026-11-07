import hashlib
import json

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from delivery.models import DeliveryTask
from ladya.defaults import get_or_create_ladya_settings
from ladya.models import Laboratory, Package
from ladya.services import (
    apply_manifest_sha256,
    canonical_manifest_json,
    build_package_manifest,
)


@pytest.fixture
def enable_ladya(workspace):
    row, _ = get_or_create_ladya_settings(workspace)
    row.ladya_hub_enabled = True
    row.save(update_fields=["ladya_hub_enabled", "updated_at"])
    return row


@pytest.fixture
def two_labs(workspace, enable_ladya):
    a = Laboratory.objects.create(
        workspace=workspace,
        slug="central",
        title="Центральный",
        kind=Laboratory.Kind.CENTRAL_LAD,
    )
    b = Laboratory.objects.create(
        workspace=workspace,
        slug="private",
        title="Частная",
        kind=Laboratory.Kind.PRIVATE_LAB,
    )
    return a, b


def test_package_file_respects_ladya_limit(
    authenticated_client, two_labs, settings
):
    settings.LADYA_PACKAGE_MAX_BYTES = 64
    lab_a, lab_b = two_labs
    created = authenticated_client.post(
        "/api/ladya/packages/",
        {"title": "Big", "from_laboratory": lab_a.id, "to_laboratory": lab_b.id},
        format="json",
    )
    package_id = created.data["id"]
    too_big = SimpleUploadedFile("big.bin", b"x" * 65, content_type="application/octet-stream")
    denied = authenticated_client.post(
        f"/api/ladya/packages/{package_id}/files/",
        {"file": too_big},
        format="multipart",
    )
    assert denied.status_code == 400

    ok_file = SimpleUploadedFile("ok.bin", b"x" * 64, content_type="application/octet-stream")
    uploaded = authenticated_client.post(
        f"/api/ladya/packages/{package_id}/files/",
        {"file": ok_file},
        format="multipart",
    )
    assert uploaded.status_code == 201
    assert uploaded.data["size"] == 64
    assert uploaded.data["sha256"] == hashlib.sha256(b"x" * 64).hexdigest()


def test_transfer_between_labs(authenticated_client, two_labs, user, workspace):
    lab_a, lab_b = two_labs
    package = Package.objects.create(
        workspace=workspace,
        public_number=1,
        title="Move me",
        from_laboratory=lab_a,
        to_laboratory=lab_a,
        status=Package.Status.ACCEPTED,
        created_by=user,
    )
    bad = authenticated_client.post(
        f"/api/ladya/packages/{package.id}/transfer/",
        {"to_laboratory": lab_b.id, "reason": "from draft"},
        format="json",
    )
    # status is accepted — should work
    assert bad.status_code == 200
    assert bad.data["to_laboratory"] == lab_b.id
    assert any(
        e["reason"] for e in bad.data["status_events"] if "Передача" in e["reason"] or e["reason"]
    )

    package.status = Package.Status.DRAFT
    package.save(update_fields=["status"])
    denied = authenticated_client.post(
        f"/api/ladya/packages/{package.id}/transfer/",
        {"to_laboratory": lab_a.id, "reason": "nope"},
        format="json",
    )
    assert denied.status_code == 400


def test_create_delivery_task_from_package(authenticated_client, two_labs, user, workspace):
    lab_a, lab_b = two_labs
    package = Package.objects.create(
        workspace=workspace,
        public_number=2,
        title="Need agents",
        summary="do work",
        from_laboratory=lab_a,
        to_laboratory=lab_b,
        status=Package.Status.SUBMITTED,
        created_by=user,
    )
    created = authenticated_client.post(
        f"/api/ladya/packages/{package.id}/create-delivery-task/",
        {},
        format="json",
    )
    assert created.status_code == 201
    assert created.data["package"]["linked_delivery_task"]
    task_id = created.data["delivery_task"]["id"]
    task = DeliveryTask.objects.get(pk=task_id)
    assert task.status == DeliveryTask.Status.DRAFT
    assert task.assignee_id is None
    assert "Ladya" in task.title

    again = authenticated_client.post(
        f"/api/ladya/packages/{package.id}/create-delivery-task/",
        {},
        format="json",
    )
    assert again.status_code == 400


def test_convert_requires_to_laboratory(authenticated_client, two_labs):
    lab_a, _ = two_labs
    intake = authenticated_client.post(
        "/api/ladya/intake/",
        {"body": "Нужна помощь лаборатории с методологией", "contact": "a@b.c"},
        format="json",
    )
    assert intake.status_code == 201
    denied = authenticated_client.post(
        f"/api/ladya/intake/{intake.data['id']}/convert/",
        {"title": "x"},
        format="json",
    )
    assert denied.status_code == 400

    ok = authenticated_client.post(
        f"/api/ladya/intake/{intake.data['id']}/convert/",
        {"to_laboratory": lab_a.id},
        format="json",
    )
    assert ok.status_code == 201
    assert ok.data["package"]["to_laboratory"] == lab_a.id
    assert ok.data["intake"]["status"] == "converted"


def test_manifest_hash_stable(workspace, user, two_labs):
    lab_a, lab_b = two_labs
    package = Package.objects.create(
        workspace=workspace,
        public_number=3,
        title="Manifest",
        from_laboratory=lab_a,
        to_laboratory=lab_b,
        status=Package.Status.DRAFT,
        created_by=user,
    )
    m1, d1 = apply_manifest_sha256(package)
    m2 = build_package_manifest(package)
    d2 = hashlib.sha256(
        canonical_manifest_json(m2).encode("utf-8")
    ).hexdigest()
    assert d1 == d2
    assert package.manifest_sha256 == d1
    assert json.loads(canonical_manifest_json(m1))["title"] == "Manifest"


def test_package_filters_and_events(authenticated_client, two_labs, user, workspace):
    lab_a, lab_b = two_labs
    Package.objects.create(
        workspace=workspace,
        public_number=10,
        title="Alpha pack",
        from_laboratory=lab_a,
        to_laboratory=lab_b,
        status=Package.Status.DRAFT,
        created_by=user,
    )
    Package.objects.create(
        workspace=workspace,
        public_number=11,
        title="Beta other",
        from_laboratory=lab_b,
        to_laboratory=lab_a,
        status=Package.Status.ACCEPTED,
        created_by=user,
    )
    filtered = authenticated_client.get(
        f"/api/ladya/packages/?status=accepted&to_lab={lab_a.id}&q=Beta"
    )
    assert filtered.status_code == 200
    assert len(filtered.data) == 1
    assert filtered.data[0]["title"] == "Beta other"

    lab_pkgs = authenticated_client.get(
        f"/api/ladya/laboratories/{lab_a.id}/packages/?direction=outgoing"
    )
    assert lab_pkgs.status_code == 200
    assert any(p["title"] == "Alpha pack" for p in lab_pkgs.data["packages"])

    events = authenticated_client.get("/api/ladya/events/?limit=5")
    assert events.status_code == 200
