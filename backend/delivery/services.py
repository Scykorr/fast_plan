"""Business rules for Agent Ops delivery tasks (TZ-complete)."""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from delivery.models import (
    AgentActionLog,
    AgentProfile,
    DeliveryTask,
    TaskBlocker,
    TaskComment,
    TaskDependency,
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
        DeliveryTask.Status.NEEDS_REWORK,
        DeliveryTask.Status.READY_FOR_OWNER,
    },
    DeliveryTask.Status.BLOCKED: {
        DeliveryTask.Status.IN_PROGRESS,
        DeliveryTask.Status.READY,
        DeliveryTask.Status.ASSIGNED,
        DeliveryTask.Status.NEEDS_REWORK,
    },
    DeliveryTask.Status.REVIEW: {
        DeliveryTask.Status.QA,
        DeliveryTask.Status.IN_PROGRESS,
        DeliveryTask.Status.DONE,
        DeliveryTask.Status.NEEDS_REWORK,
        DeliveryTask.Status.READY_FOR_OWNER,
    },
    DeliveryTask.Status.QA: {
        DeliveryTask.Status.DONE,
        DeliveryTask.Status.IN_PROGRESS,
        DeliveryTask.Status.REVIEW,
        DeliveryTask.Status.NEEDS_REWORK,
        DeliveryTask.Status.READY_FOR_OWNER,
    },
    DeliveryTask.Status.NEEDS_REWORK: {
        DeliveryTask.Status.ASSIGNED,
        DeliveryTask.Status.IN_PROGRESS,
        DeliveryTask.Status.BLOCKED,
        DeliveryTask.Status.READY,
        DeliveryTask.Status.QA,
        DeliveryTask.Status.READY_FOR_OWNER,
        DeliveryTask.Status.REVIEW,
    },
    DeliveryTask.Status.READY_FOR_OWNER: {
        DeliveryTask.Status.DONE,
        DeliveryTask.Status.NEEDS_REWORK,
        DeliveryTask.Status.IN_PROGRESS,
        DeliveryTask.Status.ASSIGNED,
        DeliveryTask.Status.REVIEW,
    },
    DeliveryTask.Status.DONE: {DeliveryTask.Status.ARCHIVED},
    DeliveryTask.Status.ARCHIVED: set(),
}

ALLOWED_HANDOFFS: set[tuple[str, str]] = {
    ("documentation", "smart_contract"),
    ("documentation", "backend"),
    ("documentation", "frontend"),
    ("documentation", "qa"),
    ("documentation", "owner"),
    ("smart_contract", "qa"),
    ("smart_contract", "backend"),
    ("backend", "qa"),
    ("backend", "frontend"),
    ("backend", "owner"),
    ("frontend", "qa"),
    ("frontend", "backend"),
    ("frontend", "owner"),
    ("qa", "documentation"),
    ("qa", "backend"),
    ("qa", "frontend"),
    ("qa", "smart_contract"),
    ("qa", "owner"),
    ("owner", "backend"),
    ("owner", "frontend"),
    ("owner", "documentation"),
    ("owner", "qa"),
    ("owner", "planner"),
    ("planner", "backend"),
    ("planner", "frontend"),
    ("planner", "documentation"),
    ("planner", "qa"),
    ("planner", "owner"),
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

# Delivery / human report fields (own work + GitHub links)
OWN_REPORT_FIELDS = frozenset(
    {
        "description",
        "context",
        "result_artifact",
        "expected_checks",
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
        "next_role",
        "implementation_summary",
        "expected_next_step",
        "github_commits",
    }
)

DOCUMENTATION_EDITABLE_FIELDS = frozenset(
    OWN_REPORT_FIELDS
    | MEANING_FIELDS
    | {
        "description",
        "context",
        "task_type",
        "priority",
        "assignee_role",
        "assignee",
        "ready_criterion",
        "done_criterion",
        "epic",
        "sprint",
        "project",
    }
)

# TZ §4 / §12 — role → editable task fields (None = unrestricted)
ROLE_EDITABLE_FIELDS: dict[str, frozenset[str] | None] = {
    "owner": None,
    "planner": None,
    "documentation": DOCUMENTATION_EDITABLE_FIELDS,
    "smart_contract": OWN_REPORT_FIELDS | MEANING_FIELDS,
    "backend": OWN_REPORT_FIELDS | MEANING_FIELDS,
    "frontend": OWN_REPORT_FIELDS | MEANING_FIELDS,
    "qa": OWN_REPORT_FIELDS | MEANING_FIELDS | {"done_criterion"},
    "reviewer": frozenset({"github_review_notes", "description"}),
    "human": OWN_REPORT_FIELDS | MEANING_FIELDS,
    "observer": frozenset(),
}


def editable_fields_for_profile(profile: AgentProfile | None) -> frozenset[str] | None:
    """None means unrestricted (workspace editor / owner / planner)."""
    if profile is None:
        return None
    if profile.role in ("owner", "planner"):
        return None
    return ROLE_EDITABLE_FIELDS.get(profile.role, frozenset())


def assert_fields_editable(profile: AgentProfile | None, field_names: set[str]):
    allowed = editable_fields_for_profile(profile)
    if allowed is None:
        return
    denied = sorted(field_names - allowed)
    if denied:
        from rest_framework.exceptions import PermissionDenied

        raise PermissionDenied(
            f"Role '{profile.role}' cannot edit fields: {', '.join(denied)}"
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
    "previous_assignee_id",
    "ready_criterion",
    "done_criterion",
    "scope_in",
    "scope_out",
    "expected_checks",
    "result_artifact",
    "implementation_summary",
    "expected_next_step",
    "next_role",
    "canon_url",
    "architecture_url",
    "planning_doc_url",
    "acceptance_url",
    "external_pack_url",
    "github_repo",
    "github_branch",
    "github_commit",
    "github_commits",
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
    """Fields required before moving to Ready (TZ §8 + §11 source docs)."""
    errors = []
    for field in READY_REQUIRED_FIELDS:
        value = getattr(task, field, "")
        if value is None or not str(value).strip():
            errors.append(field)
    if not (task.architecture_url or "").strip():
        errors.append("architecture_url")
    if not (task.acceptance_url or "").strip():
        errors.append("acceptance_url")
    return errors


def unfinished_dependency_ids(task: DeliveryTask) -> list[int]:
    done = {DeliveryTask.Status.DONE, DeliveryTask.Status.ARCHIVED}
    return list(
        task.dependencies.exclude(depends_on__status__in=done).values_list(
            "depends_on_id", flat=True
        )
    )


def assert_dependencies_satisfied(task: DeliveryTask):
    blocked = unfinished_dependency_ids(task)
    if blocked:
        raise ValueError(
            f"Unfinished dependencies block progress: {', '.join(map(str, blocked))}"
        )


def would_create_dependency_cycle(task_id: int, depends_on_id: int) -> bool:
    """True if adding task → depends_on creates a cycle."""
    if task_id == depends_on_id:
        return True
    seen: set[int] = set()
    stack = [depends_on_id]
    while stack:
        current = stack.pop()
        if current == task_id:
            return True
        if current in seen:
            continue
        seen.add(current)
        stack.extend(
            TaskDependency.objects.filter(task_id=current).values_list(
                "depends_on_id", flat=True
            )
        )
    return False


def profile_may(profile: AgentProfile | None, action: str) -> bool:
    """TZ §4/§12 — enforce role action sets for agent profiles."""
    if profile is None:
        return True
    if not profile.is_active:
        return False
    if profile.role == "observer" and action != "read":
        return False
    if profile.role in ("owner", "planner") and action != "close_epic":
        # owners/planners retain broad write; close_epic still via can()
        if action == "close_epic":
            return profile.can("close_epic") or profile.role in ("owner", "planner")
        return True
    if profile.can(action):
        return True
    if action == "write_task_own" and profile.can("write_task"):
        return True
    if action == "review" and profile.role in ("qa", "reviewer", "owner"):
        return True
    return False


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
    if to_status in (
        DeliveryTask.Status.IN_PROGRESS,
        DeliveryTask.Status.ASSIGNED,
    ):
        assert_dependencies_satisfied(task)
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
        DeliveryTask.Status.NEEDS_REWORK,
        DeliveryTask.Status.QA,
        DeliveryTask.Status.READY_FOR_OWNER,
    ):
        raise ValueError("Only Ready/Assigned/Needs rework/QA tasks can be claimed")
    if expected_version is not None and locked.version != expected_version:
        raise ValueError("Version conflict — task was updated")
    if locked.assignee_id and locked.assignee_id != user.id:
        raise ValueError("Task already claimed by another assignee")
    assert_dependencies_satisfied(locked)
    before = snapshot_task(locked)
    locked.assignee = user
    locked.save(update_fields=["assignee", "updated_at"])
    record_field_changes(locked, user=user, before=before, after=snapshot_task(locked))
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


@transaction.atomic
def assign_task(
    task: DeliveryTask, *, user, assignee_id: int | None, assignee_role: str | None = None
) -> DeliveryTask:
    """TZ §9.2.8 — explicit assign / unassign with field journal."""
    locked = DeliveryTask.objects.select_for_update().get(pk=task.pk)
    before = snapshot_task(locked)
    if locked.assignee_id != assignee_id:
        locked.previous_assignee_id = locked.assignee_id
        update = ["assignee", "previous_assignee", "updated_at"]
    else:
        update = ["assignee", "updated_at"]
    locked.assignee_id = assignee_id
    if assignee_role is not None:
        locked.assignee_role = assignee_role
        update.append("assignee_role")
    locked.version += 1
    update.append("version")
    locked.save(update_fields=update)
    record_field_changes(locked, user=user, before=before, after=snapshot_task(locked))
    if (
        assignee_id
        and locked.status == DeliveryTask.Status.READY
    ):
        change_status(
            locked,
            to_status=DeliveryTask.Status.ASSIGNED,
            user=user,
            reason="assigned",
        )
        locked.refresh_from_db()
    elif assignee_id is None and locked.status == DeliveryTask.Status.ASSIGNED:
        change_status(
            locked,
            to_status=DeliveryTask.Status.READY,
            user=user,
            reason="unassigned",
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
    to_user_id: int | None = None,
    reason: str = "",
    expected_next_step: str = "",
) -> TaskHandoff:
    from django.contrib.auth import get_user_model

    User = get_user_model()
    pair = (from_role, to_role)
    if not from_role or not to_role:
        raise ValueError("from_role and to_role are required")
    if from_role != to_role and pair not in ALLOWED_HANDOFFS:
        raise ValueError(f"Handoff {from_role} → {to_role} is not allowed")
    if not (done_summary or "").strip():
        raise ValueError("done_summary is required")
    to_user = None
    if to_user_id:
        to_user = User.objects.filter(pk=to_user_id).first()
        if to_user is None:
            raise ValueError("to_user not found")
    else:
        profile = (
            AgentProfile.objects.filter(
                workspace=task.workspace, role=to_role, is_active=True
            )
            .order_by("id")
            .first()
        )
        if profile is not None:
            to_user = profile.user
    next_step = (expected_next_step or left_summary or "").strip()
    handoff = TaskHandoff.objects.create(
        task=task,
        from_role=from_role,
        to_role=to_role,
        from_user=user,
        to_user=to_user,
        reason=reason or "",
        expected_next_step=next_step,
        done_summary=done_summary,
        left_summary=left_summary or "",
        branch_or_pr_url=branch_or_pr_url or "",
        checks_url=checks_url or "",
        open_questions=open_questions or "",
        needs_owner_decision=needs_owner_decision,
        created_by=user,
    )
    body_parts = [f"Передача {from_role} → {to_role}: {done_summary}"]
    if reason:
        body_parts.append(f"Причина: {reason}")
    if next_step:
        body_parts.append(f"Ожидание: {next_step}")
    TaskComment.objects.create(
        task=task,
        kind=TaskComment.Kind.HANDOFF_NOTE,
        body=" | ".join(body_parts),
        author=user,
    )
    if needs_owner_decision:
        TaskComment.objects.create(
            task=task,
            kind=TaskComment.Kind.OWNER_REQUEST,
            body=open_questions or "Owner decision requested via handoff",
            author=user,
        )
    before = snapshot_task(task)
    task.previous_assignee = task.assignee
    task.assignee_role = to_role
    task.next_role = to_role
    task.assignee = to_user
    task.expected_next_step = next_step
    impl_roles = {"backend", "frontend", "smart_contract", "documentation"}
    if from_role in impl_roles and (done_summary or "").strip():
        task.implementation_summary = done_summary.strip()
    update_fields = [
        "previous_assignee",
        "assignee_role",
        "next_role",
        "assignee",
        "expected_next_step",
        "implementation_summary",
        "updated_at",
    ]
    task.save(update_fields=update_fields)
    record_field_changes(task, user=user, before=before, after=snapshot_task(task))
    rework_roles = {"backend", "frontend", "smart_contract", "documentation"}
    if to_role == "qa":
        target = DeliveryTask.Status.QA
        reason_status = "handoff to QA"
    elif to_role == "owner":
        target = DeliveryTask.Status.READY_FOR_OWNER
        reason_status = "handoff to owner"
    elif from_role == "qa" and to_role in rework_roles:
        target = DeliveryTask.Status.NEEDS_REWORK
        reason_status = "returned for rework"
    elif to_user is not None:
        target = DeliveryTask.Status.ASSIGNED
        reason_status = "handoff assigned"
    else:
        target = DeliveryTask.Status.READY
        reason_status = "handoff"
    change_status(task, to_status=target, user=user, reason=reason_status)
    return handoff


def bucket_my_delivery_tasks(workspace, user) -> dict:
    """Inbox buckets for the current assignee (agent or human)."""
    profile = AgentProfile.objects.filter(
        workspace=workspace, user=user, is_active=True
    ).first()
    qs = DeliveryTask.objects.filter(workspace=workspace).exclude(
        status__in=[DeliveryTask.Status.DONE, DeliveryTask.Status.ARCHIVED]
    )
    mine = qs.filter(assignee=user)
    role_unassigned = qs.none()
    if profile is not None:
        role_unassigned = qs.filter(
            assignee__isnull=True, assignee_role=profile.role
        )
    combined = (mine | role_unassigned).select_related(
        "assignee", "previous_assignee", "epic", "project"
    ).distinct()

    def ids(status_set):
        return list(combined.filter(status__in=status_set).order_by("-updated_at")[:100])

    return {
        "new_assignments": ids(
            [DeliveryTask.Status.ASSIGNED, DeliveryTask.Status.READY]
        ),
        "in_progress": ids([DeliveryTask.Status.IN_PROGRESS]),
        "waiting_response": ids(
            [
                DeliveryTask.Status.QA,
                DeliveryTask.Status.REVIEW,
                DeliveryTask.Status.READY_FOR_OWNER,
            ]
        ),
        "returned_for_rework": ids([DeliveryTask.Status.NEEDS_REWORK]),
        "blocked": ids([DeliveryTask.Status.BLOCKED]),
    }


def resolve_blocker(blocker: TaskBlocker, *, user, note: str = "") -> TaskBlocker:
    if blocker.resolved_at or blocker.cancelled_at:
        return blocker
    blocker.resolved_at = timezone.now()
    blocker.resolved_by = user
    blocker.resolution_note = note or ""
    blocker.save(
        update_fields=["resolved_at", "resolved_by", "resolution_note"]
    )
    TaskComment.objects.create(
        task=blocker.task,
        kind=TaskComment.Kind.BLOCKER_NOTE,
        body=f"Blocker resolved: {blocker.title}"
        + (f" — {note}" if note else ""),
        author=user,
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


def build_task_timeline(task: DeliveryTask) -> list[dict]:
    """Unified §13 journal: create + status, fields, handoffs, blockers, comments."""
    events: list[dict] = [
        {
            "kind": "created",
            "at": task.created_at.isoformat(),
            "actor_id": task.created_by_id,
            "summary": f"Task created: {task.title}",
            "detail": "",
        }
    ]
    for row in task.status_history.all():
        events.append(
            {
                "kind": "status",
                "at": row.created_at.isoformat(),
                "actor_id": row.changed_by_id,
                "summary": f"{row.from_status or '∅'} → {row.to_status}",
                "detail": row.reason,
            }
        )
    for row in task.field_history.all()[:300]:
        events.append(
            {
                "kind": "field",
                "at": row.created_at.isoformat(),
                "actor_id": row.changed_by_id,
                "summary": f"{row.field}: {row.old_value or '∅'} → {row.new_value}",
                "detail": "",
            }
        )
    for row in task.handoffs.all():
        events.append(
            {
                "kind": "handoff",
                "at": row.created_at.isoformat(),
                "actor_id": row.created_by_id,
                "summary": f"{row.from_role} → {row.to_role}",
                "detail": row.done_summary,
            }
        )
    for row in task.blockers.all():
        events.append(
            {
                "kind": "blocker",
                "at": row.created_at.isoformat(),
                "actor_id": row.created_by_id,
                "summary": row.title,
                "detail": row.detail,
            }
        )
        if row.resolved_at:
            events.append(
                {
                    "kind": "blocker_resolved",
                    "at": row.resolved_at.isoformat(),
                    "actor_id": row.resolved_by_id,
                    "summary": f"Resolved: {row.title}",
                    "detail": row.resolution_note,
                }
            )
        if row.cancelled_at:
            events.append(
                {
                    "kind": "blocker_cancelled",
                    "at": row.cancelled_at.isoformat(),
                    "actor_id": row.cancelled_by_id,
                    "summary": f"Cancelled: {row.title}",
                    "detail": row.cancel_reason,
                }
            )
    for row in task.comments.all():
        events.append(
            {
                "kind": f"comment:{row.kind}",
                "at": row.created_at.isoformat(),
                "actor_id": row.author_id,
                "summary": row.body[:200],
                "detail": row.kind,
            }
        )
    for row in task.subtasks.all():
        events.append(
            {
                "kind": "subtask_created",
                "at": row.created_at.isoformat(),
                "actor_id": None,
                "summary": f"Subtask: {row.title}",
                "detail": row.status,
            }
        )
    for row in task.dependencies.all():
        events.append(
            {
                "kind": "dependency_created",
                "at": row.created_at.isoformat(),
                "actor_id": None,
                "summary": f"Depends on #{row.depends_on_id}",
                "detail": "",
            }
        )
    for row in task.github_links.all():
        events.append(
            {
                "kind": "github_link",
                "at": row.created_at.isoformat(),
                "actor_id": None,
                "summary": (
                    f"{row.repo}"
                    + (f" PR #{row.pr_number}" if row.pr_number else f" {row.branch}")
                ),
                "detail": row.checks_status or row.pr_state,
            }
        )
    for row in task.github_reviews.all()[:100]:
        events.append(
            {
                "kind": "github_review",
                "at": row.created_at.isoformat(),
                "actor_id": None,
                "summary": f"[{row.state}] {row.author_login or 'review'}",
                "detail": (row.body or "")[:200],
            }
        )
    for row in task.meaning_change_requests.all()[:100]:
        events.append(
            {
                "kind": f"meaning:{row.status}",
                "at": row.created_at.isoformat(),
                "actor_id": row.requested_by_id,
                "summary": "Meaning change: "
                + ", ".join(sorted((row.proposed_fields or {}).keys())),
                "detail": row.note or row.review_note or "",
            }
        )
    events.sort(key=lambda e: e["at"], reverse=True)
    return events[:500]
