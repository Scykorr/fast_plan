"""CRM SKU catalog + stock movements."""

from decimal import Decimal

import pytest
from rest_framework import status

from crm.models import CrmDocument, CrmSku, CrmStockMovement


@pytest.mark.django_db
def test_sku_crud_adjust_and_invoice_fulfillment(authenticated_client, workspace):
    create = authenticated_client.post(
        "/api/crm/skus/",
        {
            "code": "widget-1",
            "name": "Widget",
            "unit": "шт",
            "unit_price": "100.00",
            "qty_on_hand": "10",
        },
        format="json",
    )
    assert create.status_code == status.HTTP_201_CREATED
    assert create.data["code"] == "WIDGET-1"
    assert Decimal(create.data["qty_on_hand"]) == Decimal("10")
    sku_id = create.data["id"]

    listed = authenticated_client.get("/api/crm/skus/")
    assert listed.status_code == status.HTTP_200_OK
    assert any(row["id"] == sku_id for row in listed.data)

    adjust = authenticated_client.post(
        f"/api/crm/skus/{sku_id}/adjust/",
        {"delta": "-2", "note": "damage"},
        format="json",
    )
    assert adjust.status_code == status.HTTP_200_OK
    assert Decimal(adjust.data["qty_on_hand"]) == Decimal("8")

    moves = authenticated_client.get(f"/api/crm/skus/{sku_id}/movements/")
    assert moves.status_code == status.HTTP_200_OK
    assert len(moves.data) >= 2

    doc = authenticated_client.post(
        "/api/crm/documents/",
        {
            "doc_type": "invoice",
            "title": "Sale",
            "amount": "300",
            "status": "draft",
            "line_items": [{"sku_id": sku_id, "qty": 3}],
        },
        format="json",
    )
    assert doc.status_code == status.HTTP_201_CREATED
    assert doc.data["line_items"][0]["sku"] == "WIDGET-1"
    assert doc.data["line_items"][0]["title"] == "Widget"
    doc_id = doc.data["id"]

    paid = authenticated_client.patch(
        f"/api/crm/documents/{doc_id}/",
        {"status": "paid"},
        format="json",
    )
    assert paid.status_code == status.HTTP_200_OK
    assert paid.data["stock_fulfilled"] is True

    sku = CrmSku.objects.get(pk=sku_id)
    assert sku.qty_on_hand == Decimal("5")
    assert CrmStockMovement.objects.filter(
        sku_id=sku_id, reason=CrmStockMovement.Reason.SALE
    ).exists()

    # idempotent: second paid patch does not double-deduct
    again = authenticated_client.patch(
        f"/api/crm/documents/{doc_id}/",
        {"status": "paid"},
        format="json",
    )
    assert again.status_code == status.HTTP_200_OK
    sku.refresh_from_db()
    assert sku.qty_on_hand == Decimal("5")

    voided = authenticated_client.patch(
        f"/api/crm/documents/{doc_id}/",
        {"status": "void"},
        format="json",
    )
    assert voided.status_code == status.HTTP_200_OK
    assert voided.data["stock_fulfilled"] is False
    sku.refresh_from_db()
    assert sku.qty_on_hand == Decimal("8")

    soft = authenticated_client.delete(f"/api/crm/skus/{sku_id}/")
    assert soft.status_code == status.HTTP_204_NO_CONTENT
    assert CrmSku.objects.get(pk=sku_id).is_active is False


@pytest.mark.django_db
def test_sku_adjust_rejects_negative_without_flag(authenticated_client, workspace):
    sku = CrmSku.objects.create(
        workspace=workspace, code="LOW", name="Low", qty_on_hand=Decimal("1")
    )
    resp = authenticated_client.post(
        f"/api/crm/skus/{sku.id}/adjust/",
        {"delta": "-5"},
        format="json",
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    sku.refresh_from_db()
    assert sku.qty_on_hand == Decimal("1")
