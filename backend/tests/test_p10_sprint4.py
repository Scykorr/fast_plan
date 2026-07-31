"""P10 sprint 4: change requests + document line editor / SKU amount."""

from decimal import Decimal

import pytest
from rest_framework import status

from crm.models import CrmDocument, CrmSku
from projects.models import Project, ProjectBaseline, ProjectChangeRequest


@pytest.mark.django_db
def test_change_request_approve_creates_baseline(authenticated_client, workspace, user):
    project = Project.objects.create(
        workspace=workspace, name="CR project", manager=user
    )
    create = authenticated_client.post(
        f"/api/projects/{project.id}/change-requests/",
        {
            "title": "Add scope",
            "change_type": "scope",
            "description": "Extra WP",
            "impact_notes": "+5d",
        },
        format="json",
    )
    assert create.status_code == status.HTTP_201_CREATED
    cr_id = create.data["id"]
    assert create.data["status"] == ProjectChangeRequest.Status.SUBMITTED

    decide = authenticated_client.post(
        f"/api/change-requests/{cr_id}/decide/",
        {"action": "approve", "note": "ok", "create_baseline": True},
        format="json",
    )
    assert decide.status_code == status.HTTP_200_OK
    assert decide.data["status"] == ProjectChangeRequest.Status.APPROVED
    assert decide.data["baseline"] is not None
    assert ProjectBaseline.objects.filter(pk=decide.data["baseline"]).exists()
    assert ProjectChangeRequest.objects.get(pk=cr_id).baseline_id == decide.data["baseline"]


@pytest.mark.django_db
def test_change_request_reject_no_baseline(authenticated_client, workspace, user):
    project = Project.objects.create(
        workspace=workspace, name="CR reject", manager=user
    )
    create = authenticated_client.post(
        f"/api/projects/{project.id}/change-requests/",
        {"title": "Drop feature", "change_type": "scope"},
        format="json",
    )
    cr_id = create.data["id"]
    decide = authenticated_client.post(
        f"/api/change-requests/{cr_id}/decide/",
        {"action": "reject", "note": "out of budget"},
        format="json",
    )
    assert decide.status_code == status.HTTP_200_OK
    assert decide.data["status"] == ProjectChangeRequest.Status.REJECTED
    assert decide.data["baseline"] is None
    assert ProjectBaseline.objects.filter(project=project).count() == 0


@pytest.mark.django_db
def test_document_line_items_recompute_amount(authenticated_client, workspace, user):
    sku_a = CrmSku.objects.create(
        workspace=workspace, code="A-1", name="Widget", unit_price=Decimal("100.00")
    )
    sku_b = CrmSku.objects.create(
        workspace=workspace, code="B-2", name="Gadget", unit_price=Decimal("50.00")
    )
    create = authenticated_client.post(
        "/api/crm/documents/",
        {
            "doc_type": "quote",
            "title": "Multi-line KP",
            "recompute_amount": True,
            "line_items": [
                {"sku_id": sku_a.id, "qty": 2},
                {"sku_id": sku_b.id, "qty": 3},
            ],
        },
        format="json",
    )
    assert create.status_code == status.HTTP_201_CREATED
    assert Decimal(str(create.data["amount"])) == Decimal("350.00")
    assert len(create.data["line_items"]) == 2
    assert create.data["line_items"][0]["title"] == "Widget"

    doc_id = create.data["id"]
    patch = authenticated_client.patch(
        f"/api/crm/documents/{doc_id}/",
        {
            "recompute_amount": True,
            "line_items": [
                {"sku_id": sku_a.id, "qty": 1},
                {"sku_id": sku_b.id, "qty": 1, "price": 40},
            ],
        },
        format="json",
    )
    assert patch.status_code == status.HTTP_200_OK
    assert Decimal(str(patch.data["amount"])) == Decimal("140.00")
    doc = CrmDocument.objects.get(pk=doc_id)
    assert doc.amount == Decimal("140.00")
