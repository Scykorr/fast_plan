"""Process ops lists: stuck instances, aging tasks, SLA breaches (P10)."""

from __future__ import annotations

from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from process.models import ProcessInstance, ProcessTimer, UserTask

DEFAULT_STUCK_HOURS = 72
DEFAULT_AGING_HOURS = 48


def _hours_since(dt, now) -> float | None:
    if not dt:
        return None
    return max(0.0, (now - dt).total_seconds() / 3600.0)


def build_process_ops(
    workspace,
    *,
    stuck_hours: int = DEFAULT_STUCK_HOURS,
    aging_hours: int = DEFAULT_AGING_HOURS,
    limit: int = 50,
) -> dict:
    now = timezone.now()
    stuck_cutoff = now - timedelta(hours=max(1, stuck_hours))
    aging_cutoff = now - timedelta(hours=max(1, aging_hours))

    open_task_qs = UserTask.objects.filter(
        workspace=workspace, status=UserTask.Status.OPEN
    )

    active_ids_with_open = set(
        open_task_qs.values_list("instance_id", flat=True).distinct()
    )
    overdue_timer_instance_ids = set(
        ProcessTimer.objects.filter(
            instance__workspace=workspace,
            fired=False,
            fire_at__lt=now,
        ).values_list("instance_id", flat=True)
    )

    stuck_instances = []
    candidates = (
        ProcessInstance.objects.filter(workspace=workspace)
        .filter(
            Q(status=ProcessInstance.Status.ERROR)
            | Q(status=ProcessInstance.Status.ACTIVE, started_at__lt=stuck_cutoff)
        )
        .select_related("deployment__definition")
        .order_by("started_at")[: limit * 3]
    )
    for inst in candidates:
        age = _hours_since(inst.started_at, now)
        reasons = []
        if inst.status == ProcessInstance.Status.ERROR:
            reasons.append("error")
        if (inst.error_message or "").strip():
            reasons.append("error_message")
        if (
            inst.status == ProcessInstance.Status.ACTIVE
            and inst.id not in active_ids_with_open
            and inst.started_at
            and inst.started_at < stuck_cutoff
        ):
            reasons.append("no_open_tasks")
        if inst.id in overdue_timer_instance_ids:
            reasons.append("overdue_timer")
        if not reasons:
            continue
        stuck_instances.append(
            {
                "id": inst.id,
                "definition_name": (
                    inst.deployment.definition.name
                    if inst.deployment_id and inst.deployment.definition_id
                    else ""
                ),
                "business_key": inst.business_key,
                "status": inst.status,
                "error_message": (inst.error_message or "")[:500],
                "started_at": inst.started_at.isoformat() if inst.started_at else None,
                "age_hours": round(age, 2) if age is not None else None,
                "deal": inst.deal_id,
                "project": inst.project_id,
                "reasons": reasons,
            }
        )
        if len(stuck_instances) >= limit:
            break

    aging_tasks = []
    for task in (
        open_task_qs.filter(created_at__lt=aging_cutoff)
        .select_related("instance", "instance__deployment__definition")
        .order_by("created_at")[:limit]
    ):
        aging_tasks.append(
            {
                "id": task.id,
                "name": task.name,
                "instance_id": task.instance_id,
                "definition_name": (
                    task.instance.deployment.definition.name
                    if task.instance.deployment_id
                    and task.instance.deployment.definition_id
                    else ""
                ),
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "age_hours": round(_hours_since(task.created_at, now) or 0, 2),
                "due_at": task.due_at.isoformat() if task.due_at else None,
                "deal": task.instance.deal_id if task.instance_id else None,
                "project": task.instance.project_id if task.instance_id else None,
            }
        )

    sla_breaches = []
    for task in (
        open_task_qs.filter(due_at__isnull=False, due_at__lt=now)
        .select_related("instance", "instance__deployment__definition")
        .order_by("due_at")[:limit]
    ):
        overdue = _hours_since(task.due_at, now)
        sla_breaches.append(
            {
                "id": task.id,
                "name": task.name,
                "instance_id": task.instance_id,
                "definition_name": (
                    task.instance.deployment.definition.name
                    if task.instance.deployment_id
                    and task.instance.deployment.definition_id
                    else ""
                ),
                "due_at": task.due_at.isoformat() if task.due_at else None,
                "overdue_hours": round(overdue or 0, 2),
                "deal": task.instance.deal_id if task.instance_id else None,
                "project": task.instance.project_id if task.instance_id else None,
            }
        )

    return {
        "thresholds": {
            "stuck_hours": stuck_hours,
            "aging_hours": aging_hours,
        },
        "stuck_instances": stuck_instances,
        "aging_tasks": aging_tasks,
        "sla_breaches": sla_breaches,
        "counts": {
            "stuck_instances": len(stuck_instances),
            "aging_tasks": len(aging_tasks),
            "sla_breaches": len(sla_breaches),
            "open_user_tasks": open_task_qs.count(),
        },
    }
