"""Process metrics (P8f)."""

from __future__ import annotations

from django.db.models import Count
from django.utils import timezone

from process.models import ProcessInstance, UserTask


def build_process_metrics(workspace) -> dict:
    instances = ProcessInstance.objects.filter(workspace=workspace)
    open_tasks = UserTask.objects.filter(
        workspace=workspace, status=UserTask.Status.OPEN
    )
    completed = instances.filter(status=ProcessInstance.Status.COMPLETED).exclude(
        completed_at=None
    )
    cycle = None
    if completed.exists():
        durations = []
        for row in completed.only("started_at", "completed_at")[:500]:
            if row.completed_at and row.started_at:
                durations.append(
                    (row.completed_at - row.started_at).total_seconds() / 3600.0
                )
        if durations:
            cycle = sum(durations) / len(durations)

    overdue = open_tasks.filter(due_at__isnull=False, due_at__lt=timezone.now()).count()

    by_status = {
        row["status"]: row["c"]
        for row in instances.values("status").annotate(c=Count("id"))
    }
    return {
        "instance_count": instances.count(),
        "active_count": instances.filter(status=ProcessInstance.Status.ACTIVE).count(),
        "completed_count": instances.filter(
            status=ProcessInstance.Status.COMPLETED
        ).count(),
        "error_count": instances.filter(status=ProcessInstance.Status.ERROR).count(),
        "open_user_tasks": open_tasks.count(),
        "overdue_user_tasks": overdue,
        "avg_cycle_hours": cycle,
        "by_status": by_status,
    }
