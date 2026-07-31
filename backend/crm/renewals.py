"""Contract renewals + ARR lite helpers."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from crm.models import CrmDocument, DealTask
from notifications.models import Notification
from notifications.services import create_notification


def renewals_summary(workspace, *, within_days: int = 90) -> dict:
    today = timezone.localdate()
    horizon = today + timedelta(days=max(0, int(within_days)))
    qs = (
        CrmDocument.objects.filter(
            workspace=workspace,
            doc_type=CrmDocument.DocType.CONTRACT,
        )
        .exclude(status=CrmDocument.Status.VOID)
        .select_related("organization", "person", "deal")
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
                    "deal_id": doc.deal_id,
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


def send_renewal_reminders(
    *,
    workspace=None,
    within_days: int = 30,
    dry_run: bool = False,
) -> dict:
    """Create DealTasks + in-app notifications for contracts nearing renewal.

    Idempotent via notification dedupe_key and open DealTask title match.
    Contracts without a deal get notify-only (workspace members / deal owner N/A).
    """
    today = timezone.localdate()
    horizon = today + timedelta(days=max(0, int(within_days)))
    qs = (
        CrmDocument.objects.filter(
            doc_type=CrmDocument.DocType.CONTRACT,
            renewal_date__gte=today,
            renewal_date__lte=horizon,
        )
        .exclude(status=CrmDocument.Status.VOID)
        .select_related("deal", "deal__owner", "organization", "workspace")
    )
    if workspace is not None:
        qs = qs.filter(workspace=workspace)

    created_tasks = 0
    created_notifications = 0
    skipped = 0
    items = []

    for doc in qs:
        dedupe = f"renewal:{doc.id}:{doc.renewal_date.isoformat()}"
        title = f"Продление: {doc.title or doc.number or f'#{doc.id}'}"
        link = "/crm-commerce"
        message = (
            f"Договор {doc.number or doc.id} продлевается "
            f"{doc.renewal_date.isoformat()} (через {(doc.renewal_date - today).days} дн.)"
        )

        task_created = False
        if doc.deal_id:
            open_exists = DealTask.objects.filter(
                deal_id=doc.deal_id,
                title=title,
                is_done=False,
            ).exists()
            if not open_exists and not dry_run:
                DealTask.objects.create(
                    deal_id=doc.deal_id,
                    title=title,
                    due_date=doc.renewal_date,
                    assignee=getattr(doc.deal, "owner", None),
                    notes=f"Auto renewal reminder ({dedupe})",
                    remind_before_days=7,
                )
                created_tasks += 1
                task_created = True
            elif open_exists:
                skipped += 1

        notify_user = None
        if doc.deal_id and getattr(doc.deal, "owner_id", None):
            notify_user = doc.deal.owner
        if notify_user is None and doc.workspace_id:
            from workspaces.models import WorkspaceMember

            member = (
                WorkspaceMember.objects.filter(workspace_id=doc.workspace_id)
                .select_related("user")
                .order_by("id")
                .first()
            )
            if member:
                notify_user = member.user

        notif_created = False
        if notify_user and not dry_run:
            _, notif_created = create_notification(
                user=notify_user,
                workspace=doc.workspace,
                notification_type=Notification.NotificationType.DEADLINE,
                title=title,
                message=message,
                link=link,
                dedupe_key=dedupe,
            )
            if notif_created:
                created_notifications += 1
            else:
                skipped += 1
        elif dry_run:
            items.append(
                {
                    "document_id": doc.id,
                    "deal_id": doc.deal_id,
                    "would_create_task": bool(doc.deal_id),
                    "would_notify": bool(notify_user),
                }
            )
            continue

        items.append(
            {
                "document_id": doc.id,
                "deal_id": doc.deal_id,
                "task_created": task_created,
                "notification_created": notif_created,
            }
        )

    return {
        "created_tasks": created_tasks,
        "created_notifications": created_notifications,
        "skipped": skipped,
        "within_days": within_days,
        "dry_run": dry_run,
        "items": items,
    }
