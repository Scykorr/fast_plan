"""CRM analytics aggregates for P6i."""

from __future__ import annotations

from decimal import Decimal

from django.db.models import Avg, Count, Q, Sum
from django.db.models.functions import Coalesce

from crm.models import Deal, Lead
from finance.models import Transaction


def build_crm_analytics(workspace) -> dict:
    leads = Lead.objects.filter(workspace=workspace)
    lead_total = leads.count()
    lead_converted = leads.filter(status=Lead.Status.CONVERTED).count()
    conversion = (lead_converted / lead_total * 100) if lead_total else 0.0

    by_source = list(
        leads.values("source")
        .annotate(
            total=Count("id"),
            converted=Count("id", filter=Q(status=Lead.Status.CONVERTED)),
        )
        .order_by("-total")
    )
    for row in by_source:
        total = row["total"] or 0
        converted = row["converted"] or 0
        row["conversion_rate"] = round((converted / total * 100) if total else 0.0, 1)

    open_deals = Deal.objects.filter(workspace=workspace).exclude(
        stage__is_won=True
    ).exclude(stage__is_lost=True)
    won_deals = Deal.objects.filter(workspace=workspace, stage__is_won=True)
    lost_deals = Deal.objects.filter(workspace=workspace, stage__is_lost=True)

    won_agg = won_deals.aggregate(
        count=Count("id"),
        total_amount=Coalesce(Sum("amount"), Decimal("0")),
        avg_check=Coalesce(Avg("amount"), Decimal("0")),
    )
    open_forecast = sum((d.amount * d.probability) / Decimal("100") for d in open_deals)

    by_owner = []
    owner_rows = (
        Deal.objects.filter(workspace=workspace)
        .values("owner_id", "owner__email")
        .annotate(
            open_count=Count("id", filter=Q(stage__is_won=False, stage__is_lost=False)),
            won_count=Count("id", filter=Q(stage__is_won=True)),
            won_amount=Coalesce(
                Sum("amount", filter=Q(stage__is_won=True)), Decimal("0")
            ),
        )
        .order_by("-won_amount")
    )
    for row in owner_rows:
        by_owner.append(
            {
                "owner_id": row["owner_id"],
                "owner_email": row["owner__email"],
                "open_count": row["open_count"],
                "won_count": row["won_count"],
                "won_amount": float(row["won_amount"] or 0),
            }
        )

    income = (
        Transaction.objects.filter(
            workspace=workspace, transaction_type=Transaction.TransactionType.INCOME
        ).aggregate(total=Coalesce(Sum("amount"), Decimal("0")))["total"]
        or Decimal("0")
    )
    expense = (
        Transaction.objects.filter(
            workspace=workspace, transaction_type=Transaction.TransactionType.EXPENSE
        ).aggregate(total=Coalesce(Sum("amount"), Decimal("0")))["total"]
        or Decimal("0")
    )

    # CAC lite: expense / converted leads when there are converted leads
    cac = float(expense / lead_converted) if lead_converted else None
    # LTV lite: avg won deal amount
    ltv = float(won_agg["avg_check"] or 0) if won_agg["count"] else None

    return {
        "leads": {
            "total": lead_total,
            "converted": lead_converted,
            "conversion_rate": round(conversion, 1),
            "by_source": by_source,
        },
        "deals": {
            "open_count": open_deals.count(),
            "won_count": won_agg["count"] or 0,
            "lost_count": lost_deals.count(),
            "won_amount": float(won_agg["total_amount"] or 0),
            "avg_check": float(won_agg["avg_check"] or 0),
            "forecast_amount": float(open_forecast),
            "by_owner": by_owner,
        },
        "finance": {
            "income_total": float(income),
            "expense_total": float(expense),
            "cac": cac,
            "ltv": ltv,
        },
    }


def build_ar_ap_summary(workspace) -> dict:
    from crm.models import CrmDocument, CrmDocumentPayment

    invoices = CrmDocument.objects.filter(
        workspace=workspace, doc_type=CrmDocument.DocType.INVOICE
    ).exclude(status=CrmDocument.Status.VOID)
    open_invoices = invoices.filter(
        status__in=[CrmDocument.Status.SENT, CrmDocument.Status.ACCEPTED]
    )
    ar_total = open_invoices.aggregate(total=Coalesce(Sum("amount"), Decimal("0")))[
        "total"
    ] or Decimal("0")
    paid = CrmDocumentPayment.objects.filter(
        document__workspace=workspace,
        document__doc_type=CrmDocument.DocType.INVOICE,
    ).aggregate(total=Coalesce(Sum("amount"), Decimal("0")))["total"] or Decimal("0")

    return {
        "ar_open_amount": float(ar_total),
        "ar_open_count": open_invoices.count(),
        "invoices_paid_amount": float(paid),
        "invoices_total_count": invoices.count(),
        "open_invoices": [
            {
                "id": inv.id,
                "number": inv.number,
                "title": inv.title,
                "amount": float(inv.amount),
                "due_date": inv.due_date.isoformat() if inv.due_date else None,
                "status": inv.status,
                "organization_name": inv.organization.name if inv.organization_id else None,
            }
            for inv in open_invoices.select_related("organization")[:50]
        ],
    }
