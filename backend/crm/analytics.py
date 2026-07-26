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

    bills = CrmDocument.objects.filter(
        workspace=workspace, doc_type=CrmDocument.DocType.BILL
    ).exclude(status=CrmDocument.Status.VOID)
    open_bills = bills.filter(
        status__in=[CrmDocument.Status.SENT, CrmDocument.Status.ACCEPTED]
    )
    ap_total = open_bills.aggregate(total=Coalesce(Sum("amount"), Decimal("0")))[
        "total"
    ] or Decimal("0")
    bills_paid = CrmDocumentPayment.objects.filter(
        document__workspace=workspace,
        document__doc_type=CrmDocument.DocType.BILL,
    ).aggregate(total=Coalesce(Sum("amount"), Decimal("0")))["total"] or Decimal("0")

    # Expense ledger rows without a linked CRM bill payment — soft AP signal
    expense_open = (
        Transaction.objects.filter(
            workspace=workspace,
            transaction_type=Transaction.TransactionType.EXPENSE,
        )
        .filter(Q(organization__isnull=False) | Q(deal__isnull=False))
        .aggregate(total=Coalesce(Sum("amount"), Decimal("0")))["total"]
        or Decimal("0")
    )

    def _doc_row(doc):
        return {
            "id": doc.id,
            "number": doc.number,
            "title": doc.title,
            "amount": float(doc.amount),
            "due_date": doc.due_date.isoformat() if doc.due_date else None,
            "status": doc.status,
            "organization_name": doc.organization.name if doc.organization_id else None,
            "deal_id": doc.deal_id,
        }

    return {
        "ar_open_amount": float(ar_total),
        "ar_open_count": open_invoices.count(),
        "invoices_paid_amount": float(paid),
        "invoices_total_count": invoices.count(),
        "open_invoices": [
            _doc_row(inv)
            for inv in open_invoices.select_related("organization")[:50]
        ],
        "ap_open_amount": float(ap_total),
        "ap_open_count": open_bills.count(),
        "bills_paid_amount": float(bills_paid),
        "bills_total_count": bills.count(),
        "expense_ledger_amount": float(expense_open),
        "open_bills": [
            _doc_row(bill) for bill in open_bills.select_related("organization")[:50]
        ],
    }


def build_crm_pnl(workspace, *, organization_id=None, deal_id=None) -> dict:
    """P&L from finance.Transaction, optionally scoped to org/deal."""
    qs = Transaction.objects.filter(workspace=workspace)
    if organization_id:
        qs = qs.filter(organization_id=organization_id)
    if deal_id:
        qs = qs.filter(deal_id=deal_id)

    income = qs.filter(transaction_type=Transaction.TransactionType.INCOME).aggregate(
        total=Coalesce(Sum("amount"), Decimal("0"))
    )["total"] or Decimal("0")
    expense = qs.filter(transaction_type=Transaction.TransactionType.EXPENSE).aggregate(
        total=Coalesce(Sum("amount"), Decimal("0"))
    )["total"] or Decimal("0")

    by_org = list(
        qs.exclude(organization_id=None)
        .values("organization_id", "organization__name")
        .annotate(
            income=Coalesce(
                Sum(
                    "amount",
                    filter=Q(transaction_type=Transaction.TransactionType.INCOME),
                ),
                Decimal("0"),
            ),
            expense=Coalesce(
                Sum(
                    "amount",
                    filter=Q(transaction_type=Transaction.TransactionType.EXPENSE),
                ),
                Decimal("0"),
            ),
        )
        .order_by("organization__name")[:100]
    )
    for row in by_org:
        row["income"] = float(row["income"])
        row["expense"] = float(row["expense"])
        row["profit"] = row["income"] - row["expense"]
        row["organization_name"] = row.pop("organization__name")

    by_deal = list(
        qs.exclude(deal_id=None)
        .values("deal_id", "deal__title")
        .annotate(
            income=Coalesce(
                Sum(
                    "amount",
                    filter=Q(transaction_type=Transaction.TransactionType.INCOME),
                ),
                Decimal("0"),
            ),
            expense=Coalesce(
                Sum(
                    "amount",
                    filter=Q(transaction_type=Transaction.TransactionType.EXPENSE),
                ),
                Decimal("0"),
            ),
        )
        .order_by("deal__title")[:100]
    )
    for row in by_deal:
        row["income"] = float(row["income"])
        row["expense"] = float(row["expense"])
        row["profit"] = row["income"] - row["expense"]
        row["deal_title"] = row.pop("deal__title")

    return {
        "organization_id": organization_id,
        "deal_id": deal_id,
        "income_total": float(income),
        "expense_total": float(expense),
        "profit": float(income - expense),
        "by_organization": by_org,
        "by_deal": by_deal,
    }


def build_cashflow_forecast(workspace, *, horizon_days: int = 90) -> dict:
    """30/60/90-day cashflow: open invoices/bills by due_date + weighted deal closes."""
    from datetime import timedelta

    from django.utils import timezone

    from crm.models import CrmDocument

    today = timezone.localdate()
    horizon_days = max(30, min(int(horizon_days or 90), 365))
    end = today + timedelta(days=horizon_days)

    buckets = [
        {"label": "30d", "days": 30, "inflow": 0.0, "outflow": 0.0, "deal_forecast": 0.0},
        {"label": "60d", "days": 60, "inflow": 0.0, "outflow": 0.0, "deal_forecast": 0.0},
        {"label": "90d", "days": 90, "inflow": 0.0, "outflow": 0.0, "deal_forecast": 0.0},
    ]
    # Trim buckets to horizon
    buckets = [b for b in buckets if b["days"] <= horizon_days]
    if not buckets:
        buckets = [
            {
                "label": f"{horizon_days}d",
                "days": horizon_days,
                "inflow": 0.0,
                "outflow": 0.0,
                "deal_forecast": 0.0,
            }
        ]

    def _bucket_for(d):
        if d is None:
            return None
        delta = (d - today).days
        if delta < 0 or delta > horizon_days:
            return None
        for bucket in buckets:
            if delta <= bucket["days"]:
                return bucket
        return buckets[-1]

    open_docs = CrmDocument.objects.filter(
        workspace=workspace,
        status__in=[CrmDocument.Status.SENT, CrmDocument.Status.ACCEPTED],
        doc_type__in=[CrmDocument.DocType.INVOICE, CrmDocument.DocType.BILL],
    ).select_related("organization", "deal")

    schedule = []
    for doc in open_docs:
        due = doc.due_date or end
        bucket = _bucket_for(due if doc.due_date else today)
        if bucket is None and doc.due_date:
            continue
        if bucket is None:
            bucket = buckets[0]
        amount = float(doc.amount)
        kind = "inflow" if doc.doc_type == CrmDocument.DocType.INVOICE else "outflow"
        if kind == "inflow":
            bucket["inflow"] += amount
        else:
            bucket["outflow"] += amount
        schedule.append(
            {
                "kind": kind,
                "source": doc.doc_type,
                "id": doc.id,
                "title": doc.title,
                "amount": amount,
                "due_date": doc.due_date.isoformat() if doc.due_date else None,
                "organization_name": (
                    doc.organization.name if doc.organization_id else None
                ),
            }
        )

    open_deals = Deal.objects.filter(workspace=workspace).exclude(
        stage__is_won=True
    ).exclude(stage__is_lost=True)
    for deal in open_deals:
        close = deal.close_date
        bucket = _bucket_for(close) if close else buckets[-1]
        if bucket is None:
            continue
        weighted = float((deal.amount * deal.probability) / Decimal("100"))
        bucket["deal_forecast"] += weighted
        schedule.append(
            {
                "kind": "deal_forecast",
                "source": "deal",
                "id": deal.id,
                "title": deal.title,
                "amount": weighted,
                "due_date": close.isoformat() if close else None,
                "organization_name": None,
            }
        )

    for bucket in buckets:
        bucket["net"] = (
            bucket["inflow"] + bucket["deal_forecast"] - bucket["outflow"]
        )

    return {
        "as_of": today.isoformat(),
        "horizon_days": horizon_days,
        "buckets": buckets,
        "schedule": sorted(
            schedule,
            key=lambda row: row["due_date"] or "9999-99-99",
        )[:100],
    }
