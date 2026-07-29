"""SKU catalog + simple stock movements (warehouse MVP, not WMS)."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django.db import transaction
from rest_framework.exceptions import ValidationError

from crm.models import CrmDocument, CrmSku, CrmStockMovement


def _as_decimal(value, default="0") -> Decimal:
    try:
        return Decimal(str(value if value is not None else default))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(default)


def apply_stock_delta(
    *,
    sku: CrmSku,
    delta: Decimal,
    reason: str,
    note: str = "",
    document: CrmDocument | None = None,
    user=None,
    allow_negative: bool = False,
) -> CrmStockMovement:
    with transaction.atomic():
        locked = CrmSku.objects.select_for_update().get(pk=sku.pk)
        new_qty = locked.qty_on_hand + delta
        if not allow_negative and new_qty < 0:
            raise ValidationError(
                {
                    "qty_on_hand": (
                        f"Insufficient stock for {locked.code}: "
                        f"on hand {locked.qty_on_hand}, delta {delta}."
                    )
                }
            )
        locked.qty_on_hand = new_qty
        locked.save(update_fields=["qty_on_hand", "updated_at"])
        return CrmStockMovement.objects.create(
            workspace=locked.workspace,
            sku=locked,
            delta=delta,
            qty_after=new_qty,
            reason=reason,
            note=(note or "")[:255],
            document=document,
            created_by=user if getattr(user, "is_authenticated", False) else None,
        )


def normalize_line_items(workspace, line_items: list | None) -> list:
    """Enrich line_items with sku code/title/price when sku_id is set."""
    if not line_items:
        return []
    out = []
    for raw in line_items:
        if not isinstance(raw, dict):
            continue
        item = dict(raw)
        sku_id = item.get("sku_id")
        if sku_id is not None and sku_id != "":
            try:
                sku = CrmSku.objects.get(
                    pk=int(sku_id), workspace=workspace, is_active=True
                )
            except (CrmSku.DoesNotExist, TypeError, ValueError) as exc:
                raise ValidationError({"line_items": f"Unknown sku_id={sku_id}."}) from exc
            item["sku_id"] = sku.id
            item["sku"] = sku.code
            if not item.get("title") and not item.get("name"):
                item["title"] = sku.name
            if item.get("price") is None and item.get("unit_price") is None:
                item["price"] = float(sku.unit_price)
            if item.get("qty") is None and item.get("quantity") is None:
                item["qty"] = 1
        out.append(item)
    return out


def fulfill_document_stock(document: CrmDocument, user=None) -> list[CrmStockMovement]:
    """Decrement SKU qty for invoice line_items when marking paid (once)."""
    if document.stock_fulfilled:
        return []
    if document.doc_type != CrmDocument.DocType.INVOICE:
        return []
    if document.status != CrmDocument.Status.PAID:
        return []

    movements: list[CrmStockMovement] = []
    with transaction.atomic():
        doc = CrmDocument.objects.select_for_update().get(pk=document.pk)
        if doc.stock_fulfilled:
            return []
        for item in doc.line_items or []:
            if not isinstance(item, dict) or not item.get("sku_id"):
                continue
            sku = CrmSku.objects.filter(
                pk=int(item["sku_id"]), workspace=doc.workspace
            ).first()
            if sku is None:
                continue
            qty = _as_decimal(item.get("qty") or item.get("quantity") or 1)
            if qty <= 0:
                continue
            movements.append(
                apply_stock_delta(
                    sku=sku,
                    delta=-qty,
                    reason=CrmStockMovement.Reason.SALE,
                    note=f"Invoice #{doc.number or doc.id}",
                    document=doc,
                    user=user,
                    allow_negative=True,
                )
            )
        doc.stock_fulfilled = True
        doc.save(update_fields=["stock_fulfilled", "updated_at"])
    return movements


def restore_document_stock(document: CrmDocument, user=None) -> list[CrmStockMovement]:
    """Restore SKU qty when a fulfilled invoice is voided."""
    if not document.stock_fulfilled:
        return []
    if document.doc_type != CrmDocument.DocType.INVOICE:
        return []

    movements: list[CrmStockMovement] = []
    with transaction.atomic():
        doc = CrmDocument.objects.select_for_update().get(pk=document.pk)
        if not doc.stock_fulfilled:
            return []
        for item in doc.line_items or []:
            if not isinstance(item, dict) or not item.get("sku_id"):
                continue
            sku = CrmSku.objects.filter(
                pk=int(item["sku_id"]), workspace=doc.workspace
            ).first()
            if sku is None:
                continue
            qty = _as_decimal(item.get("qty") or item.get("quantity") or 1)
            if qty <= 0:
                continue
            movements.append(
                apply_stock_delta(
                    sku=sku,
                    delta=qty,
                    reason=CrmStockMovement.Reason.VOID_RESTORE,
                    note=f"Void invoice #{doc.number or doc.id}",
                    document=doc,
                    user=user,
                    allow_negative=True,
                )
            )
        doc.stock_fulfilled = False
        doc.save(update_fields=["stock_fulfilled", "updated_at"])
    return movements


def sync_document_stock_on_status_change(
    document: CrmDocument, previous_status: str, user=None
) -> None:
    if (
        document.doc_type == CrmDocument.DocType.INVOICE
        and previous_status != CrmDocument.Status.PAID
        and document.status == CrmDocument.Status.PAID
    ):
        fulfill_document_stock(document, user=user)
    elif (
        document.doc_type == CrmDocument.DocType.INVOICE
        and previous_status == CrmDocument.Status.PAID
        and document.status == CrmDocument.Status.VOID
    ):
        restore_document_stock(document, user=user)
