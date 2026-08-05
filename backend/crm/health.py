"""CRM customer/deal health score (read-only aggregate)."""

from __future__ import annotations

from datetime import date, timedelta

from django.utils import timezone

from crm.models import Activity, CrmDocument, Deal


def _band(score: int) -> str:
    if score >= 70:
        return "healthy"
    if score >= 40:
        return "watch"
    return "at_risk"


def compute_deal_health(deal: Deal) -> dict:
    score = 50
    factors: list[dict] = []

    bant = int(getattr(deal, "qualification_score", None) or 0)
    delta = round((bant - 50) / 2)
    score += delta
    factors.append({"key": "bant", "value": bant, "delta": delta})

    today = date.today()
    overdue_count = CrmDocument.objects.filter(
        workspace=deal.workspace,
        deal=deal,
        doc_type=CrmDocument.DocType.INVOICE,
        status=CrmDocument.Status.SENT,
        due_date__lt=today,
    ).count()
    if overdue_count:
        delta = -min(30, overdue_count * 10)
        score += delta
        factors.append(
            {"key": "overdue_invoices", "value": overdue_count, "delta": delta}
        )

    renewal = None
    contract = (
        CrmDocument.objects.filter(
            workspace=deal.workspace,
            deal=deal,
            doc_type=CrmDocument.DocType.CONTRACT,
            renewal_date__isnull=False,
        )
        .order_by("renewal_date")
        .first()
    )
    if contract and contract.renewal_date:
        renewal = contract.renewal_date.isoformat()
        days = (contract.renewal_date - today).days
        if days < 0:
            delta = -20
        elif days <= 30:
            delta = -10
        elif days <= 90:
            delta = -5
        else:
            delta = 5
        score += delta
        factors.append({"key": "renewal", "value": renewal, "delta": delta})

    cutoff = timezone.now() - timedelta(days=21)
    recent = Activity.objects.filter(
        workspace=deal.workspace,
        deal=deal,
        occurred_at__gte=cutoff,
    ).exists()
    if not recent and deal.organization_id:
        recent = Activity.objects.filter(
            workspace=deal.workspace,
            organization_id=deal.organization_id,
            occurred_at__gte=cutoff,
        ).exists()
    delta = 10 if recent else -15
    score += delta
    factors.append({"key": "recent_activity", "value": recent, "delta": delta})

    score = max(0, min(100, score))
    return {
        "score": score,
        "band": _band(score),
        "deal_id": deal.id,
        "organization_id": deal.organization_id,
        "factors": factors,
        "renewal_date": renewal,
    }


def compute_organization_health(workspace, organization) -> dict:
    deals = list(
        Deal.objects.filter(workspace=workspace, organization=organization).order_by(
            "-updated_at"
        )[:20]
    )
    if not deals:
        score = 50
        factors: list[dict] = []
        today = date.today()
        overdue_count = CrmDocument.objects.filter(
            workspace=workspace,
            organization=organization,
            doc_type=CrmDocument.DocType.INVOICE,
            status=CrmDocument.Status.SENT,
            due_date__lt=today,
        ).count()
        if overdue_count:
            delta = -min(30, overdue_count * 10)
            score += delta
            factors.append(
                {"key": "overdue_invoices", "value": overdue_count, "delta": delta}
            )
        cutoff = timezone.now() - timedelta(days=21)
        recent = Activity.objects.filter(
            workspace=workspace,
            organization=organization,
            occurred_at__gte=cutoff,
        ).exists()
        delta = 10 if recent else -15
        score += delta
        factors.append({"key": "recent_activity", "value": recent, "delta": delta})
        score = max(0, min(100, score))
        return {
            "score": score,
            "band": _band(score),
            "deal_id": None,
            "organization_id": organization.id,
            "factors": factors,
            "deals_sampled": 0,
        }

    parts = [compute_deal_health(d) for d in deals]
    avg = round(sum(p["score"] for p in parts) / len(parts))
    return {
        "score": avg,
        "band": _band(avg),
        "deal_id": None,
        "organization_id": organization.id,
        "factors": [{"key": "deals_avg", "value": len(parts), "delta": 0}],
        "deals_sampled": len(parts),
        "worst_deal_id": min(parts, key=lambda p: p["score"])["deal_id"],
    }
