"""FX API views: workspace settings and exchange rates."""

from datetime import date

from decimal import Decimal, InvalidOperation

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.services import log_audit
from workspaces.fx import latest_rates, serialize_rates
from workspaces.mixins import IsWorkspaceOwner, WorkspaceMixin
from workspaces.models import ExchangeRate, Workspace


class WorkspaceSettingsView(WorkspaceMixin, APIView):
    def get(self, request):
        workspace = self.get_workspace()
        return Response(
            {
                "workspace_id": workspace.id,
                "currency": workspace.currency,
                "exchange_rates": serialize_rates(workspace),
            }
        )

    def patch(self, request):
        workspace = self.get_workspace()
        self.require_owner(workspace, request.user)
        currency = request.data.get("currency")
        if currency is not None:
            currency = str(currency).strip().upper()
            if currency not in Workspace.Currency.values:
                raise ValidationError({"currency": "Invalid currency."})
            old = workspace.currency
            workspace.currency = currency
            workspace.save(update_fields=["currency"])
            log_audit(
                workspace,
                request.user,
                "workspace.currency",
                "Workspace",
                workspace.id,
                summary=f"Changed base currency: {old} → {currency}",
                changes={"old": old, "new": currency},
            )
        return Response(
            {
                "workspace_id": workspace.id,
                "currency": workspace.currency,
                "exchange_rates": serialize_rates(workspace),
            }
        )


class ExchangeRateListCreateView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceOwner]

    def get(self, request):
        workspace = self.get_workspace()
        return Response(serialize_rates(workspace))

    def post(self, request):
        workspace = self.get_workspace()
        self.require_owner(workspace, request.user)
        currency = str(request.data.get("currency", "")).strip().upper()
        rate_raw = request.data.get("rate_to_base")
        as_of_raw = request.data.get("as_of")
        if currency not in Workspace.Currency.values:
            raise ValidationError({"currency": "Invalid currency."})
        if currency == workspace.currency:
            raise ValidationError(
                {"currency": "Base currency always has rate 1; pick another currency."}
            )
        if rate_raw in (None, ""):
            raise ValidationError({"rate_to_base": "Rate is required."})
        try:
            rate = Decimal(str(rate_raw))
        except (InvalidOperation, ValueError, TypeError) as exc:
            raise ValidationError({"rate_to_base": "Invalid rate."}) from exc
        if rate <= 0:
            raise ValidationError({"rate_to_base": "Rate must be positive."})
        if as_of_raw:
            as_of = date.fromisoformat(str(as_of_raw))
        else:
            as_of = timezone.localdate()
        row, created = ExchangeRate.objects.update_or_create(
            workspace=workspace,
            currency=currency,
            as_of=as_of,
            defaults={"rate_to_base": rate},
        )
        log_audit(
            workspace,
            request.user,
            "exchange_rate.upsert",
            "ExchangeRate",
            row.id,
            summary=f"Set {currency} rate to {rate} (base {workspace.currency})",
            changes={"currency": currency, "rate_to_base": str(rate), "as_of": as_of.isoformat()},
        )
        return Response(
            {
                "id": row.id,
                "currency": row.currency,
                "rate_to_base": str(row.rate_to_base),
                "as_of": row.as_of.isoformat(),
                "created_at": row.created_at.isoformat(),
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class ExchangeRateDetailView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceOwner]

    def delete(self, request, rate_id):
        workspace = self.get_workspace()
        row = get_object_or_404(ExchangeRate.objects.filter(workspace=workspace), pk=rate_id)
        log_audit(
            workspace,
            request.user,
            "exchange_rate.delete",
            "ExchangeRate",
            row.id,
            summary=f"Deleted {row.currency} rate ({row.as_of})",
        )
        row.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class WorkspaceFxConvertView(WorkspaceMixin, APIView):
    """Convert amounts from workspace base currency to a target currency."""

    def get(self, request):
        workspace = self.get_workspace()
        amount_raw = request.query_params.get("amount", "0")
        target = str(request.query_params.get("currency", workspace.currency)).upper()
        try:
            amount = float(amount_raw)
        except (TypeError, ValueError) as exc:
            raise ValidationError({"amount": "Invalid amount."}) from exc
        from workspaces.fx import convert_from_base

        converted = convert_from_base(amount, workspace, target)
        return Response(
            {
                "amount_base": amount,
                "base_currency": workspace.currency,
                "target_currency": target,
                "converted_amount": float(converted),
                "rates": {k: str(v) for k, v in latest_rates(workspace).items()},
            }
        )
