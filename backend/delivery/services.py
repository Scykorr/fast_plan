"""Business rules for Agent Ops delivery tasks (TZ-complete)."""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from delivery.models import (
    AgentActionLog,
    AgentProfile,
    DeliveryTask,
    TaskBlocker,
    TaskFieldHistory,
    TaskHandoff,
    TaskStatusHistory,
)

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    DeliveryTask.Status.DRAFT: {
        DeliveryTask.Status.READY,
        DeliveryTask.Status.ARCHIVED,
    },
    DeliveryTask.Status.READY: {
        DeliveryTask.Status.ASSIGNED,
        DeliveryTask.Status.IN_PROGRESS,
        DeliveryTask.Status.DRAFT,
        DeliveryTask.Status.ARCHIVED,
    },
    DeliveryTask.Status.ASSIGNED: {
        DeliveryTask.Status.IN_PROGRESS,
        DeliveryTask.Status.BLOCKED,
        DeliveryTask.Status.READY,
    },
    DeliveryTask.Status.IN_PROGRESS: {
        DeliveryTask.Status.BLOCKED,
        DeliveryTask.Status.REVIEW,
        DeliveryTask.Status.QA,
        DeliveryTask.Status.READY,
        DeliveryTask.Status.ASSIGNED,
    },
    DeliveryTask.Status.BLOCKED: {
        DeliveryTask.Status.IN_PROGRESS,
        DeliveryTask.Status.READY,
        DeliveryTask.Status.ASSIGNED,
    },
    DeliveryTask.Status.REVIEW: {
        DeliveryTask.Status.QA,
        DeliveryTask.Status.IN_PROGRESS,
        DeliveryTask.Status.DONE,
    },
    DeliveryTask.Status.QA: {
        DeliveryTask.Status.DONE,
        DeliveryTask.Status.IN_PROGRESS,
        DeliveryTask.Status.REVIEW,
    },
    DeliveryTask.Status.DONE: {DeliveryTask.Status.ARCHIVED},
    DeliveryTask.Status.ARCHIVED: set(),
}

ALLOWED_HANDOFFS: set[tuple[str, str]] = {
    ("documentation", "smart_contract"),
    ("documentation", "backend"),
    ("documentation", "frontend"),
    ("smart_contract", "qa"),
    ("backend", "qa"),
    ("frontend", "qa"),
    ("qa", "documentation"),
    ("documentation", "owner"),
}

# TZ §8 — all card sections required for Ready
READY_REQUIRED_FIELDS = (
    "title",
    "business_outcome",
    "context",
    "canon_url",
    "planning_doc_url",
    "scope_in",
    "scope_out",
    "ready_criterion",
    "done_criterion",
    "expected_checks",
    "result_artifact",
    "assignee_role",
    "next_role",
)

MEANING_FIELDS = frozenset(
    {
        "business_outcome",
        "canon_url",
        "architecture_url",
        "planning_doc_url",
        "acceptance_url",
        "scope_in",
        "scope_out",
        "title",
    }
)

TRACKED_FIELDS = (
    "title",
    "description",
    "business_outcome",
    "context",
    "task_type",
    "priority",
    "assignee_role",
    "assignee_id",
    "ready_criterion",
    "done_criterion",
    "scope_in",
    "scope_out",
    "expected_checks",
    "result_artifact",
    "next_role",
    "canon_url",
    "architecture_url",
    "planning_doc_url",
    "acceptance_url",
    "external_pack_url",
    "github_repo",
    "github_branch",
    "github_commit",
    "github_pr_url",
    "github_pr_number",
    "github_pr_state",
    "github_checks_url",
    "github_checks_status",
    "github_review_notes",
    "epic_id",
    "sprint_id",
    "project_id",
)


def ready_gate_errors(task: DeliveryTask) -> list[str]:
    """Fields required before moving to Ready (TZ §8)."""
    errors = []
    for field in READY_REQUIRED_FIELDS:
        value = getattr(task, field, "")
        if value is None or not str(value).strip():
            errors.append(field)
    # Architecture link optional if acceptance present, but TZ §11 wants docs —
    # require at least one of architecture_url or acceptance_url in addition to canon/planning
    if not (task.architecture_url or task.acceptance_url or "").strip():
        errors.append("architecture_url_or_acceptance_url")
    return errors


def log_agent_action(
    *,
    workspace,
    user,
    action: str,
    entity_type: str = "",
    entity_id: int | None = None,
    detail: str = "",
):
    profile = AgentProfile.objects.filter(
        workspace=workspace, user=user, is_active=True
    ).first()
    AgentActionLog.objects.create(
        workspace=workspace,
        profile=profile,
        user=user,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        detail=detail or "",
    )


def record_field_changes(task: DeliveryTask, *, user, before: dict, after: dict):
    for field in TRACKED_FIELDS:
        old = before.get(field)
        new = after.get(field)
        if old == new:
            continue
        TaskFieldHistory.objects.create(
            task=task,
            field=field.replace("_id", ""),
            old_value="" if old is None else str(old),
            new_value="" if new is None else str(new),
            changed_by=user,
        )


def snapshot_task(task: DeliveryTask) -> dict:
    return {f: getattr(task, f) for f in TRACKED_FIELDS}


def change_status(
    task: DeliveryTask,
    *,
    to_status: str,
    user,
    reason: str = "",
) -> DeliveryTask:
    if to_status == task.status:
        return task
    allowed = ALLOWED_TRANSITIONS.get(task.status, set())
    if to_status not in allowed:
        raise ValueError(f"Cannot transition {task.status} → {to_status}")
    if to_status == DeliveryTask.Status.READY:
        missing = ready_gate_errors(task)
        if missing:
            raise ValueError(f"Ready gate failed: missing {', '.join(missing)}")
    if to_status == DeliveryTask.Status.BLOCKED:
        if not task.blockers.filter(
            resolved_at__isnull=True, cancelled_at__isnull=True
        ).exists():
            raise ValueError("Blocked requires at least one open blocker")

    from_status = task.status
    task.status = to_status
    task.version += 1
    task.save(update_fields=["status", "version", "updated_at"])
    TaskStatusHistory.objects.create(
        task=task,
        from_status=from_status,
        to_status=to_status,
        changed_by=user,
        reason=reason or "",
    )
    return task


@transaction.atomic
def claim_task(
    task: DeliveryTask, *, user, expected_version: int | None = None
) -> DeliveryTask:
    locked = DeliveryTask.objects.select_for_update().get(pk=task.pk)
    if locked.status not in (
        DeliveryTask.Status.READY,
        DeliveryTask.Status.ASSIGNED,
    ):
        raise ValueError("Only Ready/Assigned tasks can be claimed")
    if expected_version is not None and locked.version != expected_version:
        raise ValueError("Version conflict — task was updated")
    if locked.assignee_id and locked.assignee_id != user.id:
        raise ValueError("Task already claimed by another assignee")
    locked.assignee = user
    locked.save(update_fields=["assignee", "updated_at"])
    if locked.status == DeliveryTask.Status.READY:
        change_status(
            locked,
            to_status=DeliveryTask.Status.ASSIGNED,
            user=user,
            reason="claimed",
        )
        locked.refresh_from_db()
    change_status(
        locked,
        to_status=DeliveryTask.Status.IN_PROGRESS,
        user=user,
        reason="started after claim",
    )
    locked.refresh_from_db()
    return locked


def create_handoff(
    task: DeliveryTask,
    *,
    user,
    from_role: str,
    to_role: str,
    done_summary: str,
    left_summary: str = "",
    branch_or_pr_url: str = "",
    checks_url: str = "",
    open_questions: str = "",
    needs_owner_decision: bool = False,
) -> TaskHandoff:
    pair = (from_role, to_role)
    if not from_role or not to_role:
        raise ValueError("from_role and to_role are required")
    if from_role != to_role and pair not in ALLOWED_HANDOFFS:
        raise ValueError(f"Handoff {from_role} → {to_role} is not allowed")
    if not (done_summary or "").strip():
        raise ValueError("done_summary is required")
    handoff = TaskHandoff.objects.create(
        task=task,
        from_role=from_role,
        to_role=to_role,
        done_summary=done_summary,
        left_summary=left_summary or "",
        branch_or_pr_url=branch_or_pr_url or "",
        checks_url=checks_url or "",
        open_questions=open_questions or "",
        needs_owner_decision=needs_owner_decision,
        created_by=user,
    )
    before = snapshot_task(task)
    task.assignee_role = to_role
    task.next_role = to_role
    task.assignee = None
    task.save(update_fields=["assignee_role", "next_role", "assignee", "updated_at"])
    record_field_changes(task, user=user, before=before, after=snapshot_task(task))
    if to_role == "qa":
        change_status(
            task, to_status=DeliveryTask.Status.QA, user=user, reason="handoff"
        )
    elif to_role == "owner":
        change_status(
            task,
            to_status=DeliveryTask.Status.REVIEW,
            user=user,
            reason="handoff to owner",
        )
    else:
        change_status(
            task, to_status=DeliveryTask.Status.READY, user=user, reason="handoff"
        )
    return handoff


def resolve_blocker(blocker: TaskBlocker, *, user, note: str = "") -> TaskBlocker:
    if blocker.resolved_at or blocker.cancelled_at:
        return blocker
    blocker.resolved_at = timezone.now()
    blocker.resolved_by = user
    blocker.resolution_note = note or ""
    blocker.save(
        update_fields=["resolved_at", "resolved_by", "resolution_note"]
    )
    task = blocker.task
    if (
        task.status == DeliveryTask.Status.BLOCKED
        and not task.blockers.filter(
            resolved_at__isnull=True, cancelled_at__isnull=True
        ).exists()
    ):
        change_status(
            task,
            to_status=DeliveryTask.Status.IN_PROGRESS,
            user=user,
            reason="blocker resolved",
        )
    return blocker


def cancel_blocker(
    blocker: TaskBlocker, *, user, reason: str = ""
) -> TaskBlocker:
    """Soft-cancel with trail — TZ §12 forbids silent delete."""
    if blocker.resolved_at or blocker.cancelled_at:
        return blocker
    if not (reason or "").strip():
        raise ValueError("cancel reason is required (no silent blocker removal)")
    blocker.cancelled_at = timezone.now()
    blocker.cancelled_by = user
    blocker.cancel_reason = reason.strip()
    blocker.save(
        update_fields=["cancelled_at", "cancelled_by", "cancel_reason"]
    )
    task = blocker.task
    if (
        task.status == DeliveryTask.Status.BLOCKED
        and not task.blockers.filter(
            resolved_at__isnull=True, cancelled_at__isnull=True
        ).exists()
    ):
        change_status(
            task,
            to_status=DeliveryTask.Status.IN_PROGRESS,
            user=user,
            reason=f"blocker cancelled: {reason.strip()}",
        )
    return blocker


def agent_may_close_epic(profile: AgentProfile | None) -> bool:
    if profile is None:
        return True  # workspace editor without agent profile
    if profile.role in ("owner", "planner"):
        return True
    return profile.can("close_epic")
