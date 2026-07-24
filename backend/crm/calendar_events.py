"""CRM events for the workspace calendar (deal tasks, meetings, deal close dates)."""

from __future__ import annotations

from datetime import date, datetime

from django.utils import timezone

from crm.models import Activity, Deal, DealTask


def _in_month(d: date, year: int, month: int) -> bool:
    return d.year == year and d.month == month


def workspace_crm_events(workspace, year: int, month: int) -> list[dict]:
    events: list[dict] = []

    tasks = (
        DealTask.objects.filter(
            deal__workspace=workspace,
            is_done=False,
            due_date__isnull=False,
            due_date__year=year,
            due_date__month=month,
        )
        .select_related("deal")
        .order_by("due_date", "id")
    )
    for task in tasks:
        events.append(
            {
                "id": f"deal-task-{task.id}",
                "title": f"CRM: {task.title}",
                "start": task.due_date.isoformat(),
                "allDay": True,
                "extendedProps": {
                    "event_type": "deal_task",
                    "deal_id": task.deal_id,
                    "deal_task_id": task.id,
                    "deal_title": task.deal.title,
                },
            }
        )

    meetings = (
        Activity.objects.filter(
            workspace=workspace,
            kind=Activity.Kind.MEETING,
            occurred_at__year=year,
            occurred_at__month=month,
        )
        .order_by("occurred_at", "id")
    )
    for act in meetings:
        start = timezone.localtime(act.occurred_at)
        events.append(
            {
                "id": f"meeting-{act.id}",
                "title": f"Встреча: {act.subject}",
                "start": start.isoformat(),
                "allDay": False,
                "extendedProps": {
                    "event_type": "meeting",
                    "activity_id": act.id,
                    "deal_id": act.deal_id,
                    "organization_id": act.organization_id,
                },
            }
        )

    deals = (
        Deal.objects.filter(
            workspace=workspace,
            close_date__isnull=False,
            close_date__year=year,
            close_date__month=month,
        )
        .select_related("stage")
        .order_by("close_date", "id")
    )
    for deal in deals:
        if deal.stage.is_won or deal.stage.is_lost:
            continue
        events.append(
            {
                "id": f"deal-close-{deal.id}",
                "title": f"Закрытие сделки: {deal.title}",
                "start": deal.close_date.isoformat(),
                "allDay": True,
                "extendedProps": {
                    "event_type": "deal_close",
                    "deal_id": deal.id,
                },
            }
        )

    return events


def iter_sync_payloads(workspace, *, horizon_days: int = 90) -> list[dict]:
    """Flatten upcoming CRM events for outbound calendar sync."""
    today = timezone.localdate()
    end = today.fromordinal(today.toordinal() + horizon_days)
    payloads: list[dict] = []

    tasks = DealTask.objects.filter(
        deal__workspace=workspace,
        is_done=False,
        due_date__isnull=False,
        due_date__gte=today,
        due_date__lte=end,
    ).select_related("deal")
    for task in tasks:
        payloads.append(
            {
                "source_type": "deal_task",
                "source_id": str(task.id),
                "title": f"[Fast Plan] {task.title}",
                "body": f"Deal: {task.deal.title}\n{task.notes or ''}".strip(),
                "start": datetime.combine(task.due_date, datetime.min.time()),
                "end": datetime.combine(task.due_date, datetime.min.time()),
                "all_day": True,
            }
        )

    meetings = Activity.objects.filter(
        workspace=workspace,
        kind=Activity.Kind.MEETING,
        occurred_at__date__gte=today,
        occurred_at__date__lte=end,
    )
    for act in meetings:
        start = timezone.localtime(act.occurred_at).replace(tzinfo=None)
        payloads.append(
            {
                "source_type": "meeting",
                "source_id": str(act.id),
                "title": f"[Fast Plan] {act.subject}",
                "body": act.body or "",
                "start": start,
                "end": start,
                "all_day": False,
            }
        )
    return payloads
