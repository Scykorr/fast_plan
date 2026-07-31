"""Contract renewals + ARR lite helpers."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from crm.models import CrmDocument


def renewals_summary(workspace, *, within_days: int = 90) -> dict:
    today = timezone.localdate()
    horizon = today + timedelta(days=max(0, int(within_days)))
    qs = (
        CrmDocument.objects.filter(
            workspace=workspace,
            doc_type=CrmDocument.DocType.CONTRACT,
        )
        .exclude(status=CrmDocument.Status.VOID)
        .select_related("organization", "person")
        .order_by("renewal_date", "id")
    )
    upcoming = []
    arr_total = Decimal("0")
    for doc in qs:
        annual = doc.arr_annual if doc.arr_annual else doc.amount
        if doc.status in (
            CrmDocument.Status.ACCEPTED,
            CrmDocument.Status.PAID,
            CrmDocument.Status.SENT,
        ):
            arr_total += annual or Decimal("0")
        if doc.renewal_date and today <= doc.renewal_date <= horizon:
            upcoming.append(
                {
                    "id": doc.id,
                    "title": doc.title,
                    "number": doc.number,
                    "status": doc.status,
                    "amount": str(doc.amount),
                    "arr_annual": str(annual or 0),
                    "renewal_date": doc.renewal_date.isoformat(),
                    "term_months": doc.term_months,
                    "organization_id": doc.organization_id,
                    "organization_name": (
                        doc.organization.name if doc.organization_id else None
                    ),
                    "days_until": (doc.renewal_date - today).days,
                }
            )
    return {
        "workspace_id": workspace.id,
        "as_of": today.isoformat(),
        "within_days": within_days,
        "arr_total": str(arr_total.quantize(Decimal("0.01"))),
        "upcoming": upcoming,
        "contract_count": qs.count(),
    }
