"""CRM SKU catalog + stock adjust APIs."""

from decimal import Decimal, InvalidOperation

from django.db import IntegrityError
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from crm.inventory import apply_stock_delta
from crm.models import CrmSku, CrmStockMovement
from crm.serializers import CrmSkuSerializer, CrmStockMovementSerializer
from workspaces.mixins import IsWorkspaceEditorOrReadOnly, WorkspaceMixin


def _decimal(value, field: str) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValidationError({field: "Invalid decimal."}) from exc


class CrmSkuListCreateView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get(self, request):
        qs = CrmSku.objects.filter(workspace=self.get_workspace())
        if request.query_params.get("active") != "0":
            qs = qs.filter(is_active=True)
        q = (request.query_params.get("q") or "").strip()
        if q:
            qs = qs.filter(Q(code__icontains=q) | Q(name__icontains=q))
        return Response(CrmSkuSerializer(qs[:500], many=True).data)

    def post(self, request):
        self.require_editor()
        code = (request.data.get("code") or "").strip().upper()
        name = (request.data.get("name") or "").strip()
        if not code:
            raise ValidationError({"code": "Required."})
        if not name:
            raise ValidationError({"name": "Required."})
        unit_price = _decimal(request.data.get("unit_price", 0), "unit_price")
        qty = _decimal(request.data.get("qty_on_hand", 0), "qty_on_hand")
        try:
            row = CrmSku.objects.create(
                workspace=self.get_workspace(),
                code=code,
                name=name,
                unit=(request.data.get("unit") or "шт").strip()[:32] or "шт",
                unit_price=unit_price,
                qty_on_hand=Decimal("0"),
                notes=(request.data.get("notes") or "")[:5000],
                is_active=True,
            )
        except IntegrityError as exc:
            raise ValidationError({"code": "SKU code already exists."}) from exc
        if qty != 0:
            apply_stock_delta(
                sku=row,
                delta=qty,
                reason=CrmStockMovement.Reason.RECEIVE,
                note="Initial stock",
                user=request.user,
                allow_negative=True,
            )
            row.refresh_from_db()
        return Response(CrmSkuSerializer(row).data, status=status.HTTP_201_CREATED)


class CrmSkuDetailView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get_object(self, sku_id):
        return get_object_or_404(
            CrmSku.objects.filter(workspace=self.get_workspace()), pk=sku_id
        )

    def get(self, request, sku_id):
        return Response(CrmSkuSerializer(self.get_object(sku_id)).data)

    def patch(self, request, sku_id):
        self.require_editor()
        row = self.get_object(sku_id)
        if "code" in request.data:
            code = str(request.data.get("code") or "").strip().upper()
            if not code:
                raise ValidationError({"code": "Required."})
            row.code = code
        if "name" in request.data:
            name = str(request.data.get("name") or "").strip()
            if not name:
                raise ValidationError({"name": "Required."})
            row.name = name
        if "unit" in request.data:
            row.unit = str(request.data.get("unit") or "шт").strip()[:32] or "шт"
        if "unit_price" in request.data:
            row.unit_price = _decimal(request.data.get("unit_price"), "unit_price")
        if "notes" in request.data:
            row.notes = str(request.data.get("notes") or "")[:5000]
        if "is_active" in request.data:
            row.is_active = bool(request.data.get("is_active"))
        try:
            row.save()
        except IntegrityError as exc:
            raise ValidationError({"code": "SKU code already exists."}) from exc
        return Response(CrmSkuSerializer(row).data)

    def delete(self, request, sku_id):
        self.require_editor()
        row = self.get_object(sku_id)
        row.is_active = False
        row.save(update_fields=["is_active", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class CrmSkuAdjustView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def post(self, request, sku_id):
        self.require_editor()
        row = get_object_or_404(
            CrmSku.objects.filter(workspace=self.get_workspace()), pk=sku_id
        )
        if "delta" in request.data:
            delta = _decimal(request.data.get("delta"), "delta")
        elif "qty_on_hand" in request.data:
            target = _decimal(request.data.get("qty_on_hand"), "qty_on_hand")
            delta = target - row.qty_on_hand
        else:
            raise ValidationError({"delta": "Provide delta or qty_on_hand."})
        if delta == 0:
            return Response(CrmSkuSerializer(row).data)
        reason = (request.data.get("reason") or CrmStockMovement.Reason.ADJUST).strip()
        if reason not in dict(CrmStockMovement.Reason.choices):
            reason = CrmStockMovement.Reason.ADJUST
        note = str(request.data.get("note") or "")[:255]
        apply_stock_delta(
            sku=row,
            delta=delta,
            reason=reason,
            note=note,
            user=request.user,
            allow_negative=bool(request.data.get("allow_negative")),
        )
        row.refresh_from_db()
        return Response(CrmSkuSerializer(row).data)


class CrmSkuMovementsView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get(self, request, sku_id):
        sku = get_object_or_404(
            CrmSku.objects.filter(workspace=self.get_workspace()), pk=sku_id
        )
        qs = CrmStockMovement.objects.filter(sku=sku).select_related("document")[:100]
        return Response(CrmStockMovementSerializer(qs, many=True).data)
