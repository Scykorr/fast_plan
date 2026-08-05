"""Predictive / Waterfall methodology: phases, gates, schedule freeze."""

from __future__ import annotations

from datetime import date, timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import APIException, ValidationError

from projects.baseline import create_baseline
from projects.models import (
    ActivityDependency,
    PhaseGate,
    Project,
    ScheduleActivity,
    WBSNode,
)
from projects.services import create_root_wbs_node


class ScheduleLockedError(APIException):
    status_code = 409
    default_detail = (
        "Schedule is locked after a phase gate baseline. "
        "Submit and approve a Change Request to unlock edits."
    )
    default_code = "schedule_locked"

WATERFALL_PHASES = (
    (WBSNode.PhaseKey.REQUIREMENTS, "Requirements", 10),
    (WBSNode.PhaseKey.DESIGN, "Design", 15),
    (WBSNode.PhaseKey.IMPLEMENTATION, "Implementation", 20),
    (WBSNode.PhaseKey.VERIFICATION, "Verification", 10),
    (WBSNode.PhaseKey.MAINTENANCE, "Maintenance", 5),
)

DEFAULT_GATE_CHECKLIST = [
    {"id": "deliverables", "label": "Phase deliverables accepted", "done": False},
    {"id": "risks", "label": "Risks reviewed / residual acceptable", "done": False},
    {"id": "schedule", "label": "Schedule and budget within tolerance", "done": False},
    {"id": "signoff", "label": "Sponsor / product owner sign-off", "done": False},
]


def default_gate_checklist() -> list[dict]:
    return [dict(item) for item in DEFAULT_GATE_CHECKLIST]


def get_phase_ancestor(node: WBSNode | None) -> WBSNode | None:
    current = node
    while current is not None:
        if is_phase_node(current):
            return current
        current = current.parent
    return None


def is_phase_node(node: WBSNode) -> bool:
    return node.phase_order is not None or node.gate_status is not None


def phase_queryset(project: Project):
    return project.wbs_nodes.filter(phase_order__isnull=False)


def list_project_phases(project: Project) -> list[WBSNode]:
    return list(
        phase_queryset(project)
        .select_related("schedule")
        .order_by("phase_order", "id")
    )


def serialize_phase(p: WBSNode) -> dict:
    schedule = getattr(p, "schedule", None)
    return {
        "id": p.id,
        "code": p.code,
        "title": p.title,
        "phase_key": p.phase_key,
        "phase_order": p.phase_order,
        "gate_status": p.gate_status,
        "progress": getattr(schedule, "progress", 0) or 0,
        "start_date": getattr(schedule, "start_date", None),
        "end_date": getattr(schedule, "end_date", None),
    }


def _reindex_phase_orders(project: Project) -> list[WBSNode]:
    phases = list(phase_queryset(project).order_by("phase_order", "position", "id"))
    for index, phase in enumerate(phases, start=1):
        updates = []
        if phase.phase_order != index:
            phase.phase_order = index
            updates.append("phase_order")
        if phase.position != index - 1:
            phase.position = index - 1
            updates.append("position")
        if updates:
            phase.save(update_fields=[*updates])
    return phases


def _rebuild_phase_fs_links(project: Project) -> None:
    """Keep Finish-Start chain between consecutive phase activities."""
    phases = list(
        phase_queryset(project)
        .select_related("schedule")
        .order_by("phase_order", "id")
    )
    phase_ids = [p.id for p in phases]
    activities = [
        getattr(p, "schedule", None)
        for p in phases
        if getattr(p, "schedule", None) is not None
    ]
    # Drop FS links that only connected phase nodes to each other
    ActivityDependency.objects.filter(
        predecessor__wbs_node_id__in=phase_ids,
        successor__wbs_node_id__in=phase_ids,
    ).delete()
    for pred, succ in zip(activities, activities[1:]):
        ActivityDependency.objects.get_or_create(
            predecessor=pred,
            successor=succ,
            defaults={
                "dependency_type": ActivityDependency.DependencyType.FS,
                "lag_days": 0,
            },
        )


def _normalize_open_gates(project: Project) -> None:
    """Ensure cascade: all after first non-passed are locked; first non-passed is open."""
    phases = list(phase_queryset(project).order_by("phase_order", "id"))
    seen_open_slot = False
    for phase in phases:
        if phase.gate_status == WBSNode.GateStatus.PASSED:
            continue
        if not seen_open_slot:
            if phase.gate_status != WBSNode.GateStatus.OPEN:
                phase.gate_status = WBSNode.GateStatus.OPEN
                phase.save(update_fields=["gate_status"])
            seen_open_slot = True
        else:
            if phase.gate_status != WBSNode.GateStatus.LOCKED:
                phase.gate_status = WBSNode.GateStatus.LOCKED
                phase.save(update_fields=["gate_status"])


def _ensure_root(project: Project) -> WBSNode:
    root = project.wbs_nodes.filter(parent__isnull=True).first()
    if root is None:
        root = create_root_wbs_node(project)
    return root


@transaction.atomic
def add_waterfall_phase(
    project: Project,
    *,
    title: str,
    duration_days: int = 10,
    after_phase_id: int | None = None,
    phase_key: str | None = None,
) -> WBSNode:
    assert_schedule_unlocked(project, fields={"structure"})
    title = (title or "").strip()
    if not title:
        raise ValidationError({"title": "Required."})
    duration_days = max(int(duration_days or 10), 1)
    if phase_key:
        phase_key = str(phase_key).strip()[:32] or None
        if phase_key and phase_key not in WBSNode.PhaseKey.values:
            # Free-form custom keys allowed (catalog keys preferred).
            phase_key = phase_key[:32]

    root = _ensure_root(project)
    phases = list_project_phases(project)

    insert_at = len(phases) + 1
    if after_phase_id is not None:
        after = next((p for p in phases if p.id == after_phase_id), None)
        if after is None:
            raise ValidationError({"after_phase_id": "Phase not found."})
        insert_at = (after.phase_order or 0) + 1

    # Shift following phases
    for phase in phases:
        order = phase.phase_order or 0
        if order >= insert_at:
            phase.phase_order = order + 1
            phase.position = (phase.phase_order or 1) - 1
            phase.save(update_fields=["phase_order", "position"])

    # Previous phase is the one that still has order insert_at - 1 (unshifted).
    prev = next(
        (p for p in phases if (p.phase_order or 0) == insert_at - 1),
        None,
    )

    today = date.today()
    start = today
    if prev is not None:
        prev.refresh_from_db()
        prev_schedule = getattr(prev, "schedule", None)
        if prev_schedule and prev_schedule.end_date:
            start = prev_schedule.end_date + timedelta(days=1)

    if prev and prev.gate_status != WBSNode.GateStatus.PASSED:
        gate_status = WBSNode.GateStatus.LOCKED
    else:
        gate_status = WBSNode.GateStatus.OPEN

    from projects.services import generate_wbs_code, recalculate_project_codes

    code = generate_wbs_code(project, root)
    phase = WBSNode.objects.create(
        project=project,
        parent=root,
        code=code,
        title=title,
        description=f"Waterfall phase: {title}",
        node_type=WBSNode.NodeType.DELIVERABLE,
        position=insert_at - 1,
        phase_key=phase_key,
        phase_order=insert_at,
        gate_status=gate_status,
        tracker=root.tracker,
        workflow_status=root.workflow_status,
    )
    ScheduleActivity.objects.create(
        wbs_node=phase,
        start_date=start,
        end_date=start + timedelta(days=duration_days),
        duration_days=duration_days,
        progress=0,
        is_milestone=False,
    )

    gate_ms = WBSNode.objects.create(
        project=project,
        parent=phase,
        code=generate_wbs_code(project, phase),
        title=f"Gate: {title}",
        description="Phase exit gate (go/no-go)",
        node_type=WBSNode.NodeType.MILESTONE,
        position=0,
        tracker=root.tracker,
        workflow_status=root.workflow_status,
    )
    ScheduleActivity.objects.create(
        wbs_node=gate_ms,
        start_date=start + timedelta(days=duration_days),
        end_date=start + timedelta(days=duration_days),
        duration_days=0,
        progress=0,
        is_milestone=True,
    )
    wp = WBSNode.objects.create(
        project=project,
        parent=phase,
        code=generate_wbs_code(project, phase),
        title=f"{title} work",
        description="",
        node_type=WBSNode.NodeType.WORK_PACKAGE,
        position=1,
        tracker=root.tracker,
        workflow_status=root.workflow_status,
    )
    ScheduleActivity.objects.create(
        wbs_node=wp,
        start_date=start,
        end_date=start + timedelta(days=max(duration_days - 1, 1)),
        duration_days=max(duration_days - 1, 1),
        progress=0,
        is_milestone=False,
    )

    _reindex_phase_orders(project)
    _rebuild_phase_fs_links(project)
    _normalize_open_gates(project)
    recalculate_project_codes(project)
    phase.refresh_from_db()
    return phase


@transaction.atomic
def rename_waterfall_phase(project: Project, phase: WBSNode, *, title: str) -> WBSNode:
    if phase.project_id != project.id or not is_phase_node(phase):
        raise ValidationError({"detail": "Not a Waterfall phase on this project."})
    title = (title or "").strip()
    if not title:
        raise ValidationError({"title": "Required."})
    # Rename is metadata — allowed even when schedule is locked.
    phase.title = title
    if phase.description.startswith("Waterfall phase:"):
        phase.description = f"Waterfall phase: {title}"
    phase.save(update_fields=["title", "description"])
    gate_ms = (
        phase.children.filter(node_type=WBSNode.NodeType.MILESTONE)
        .order_by("position", "id")
        .first()
    )
    if gate_ms and (
        gate_ms.title.startswith("Gate:") or gate_ms.title.startswith("Gate：")
    ):
        gate_ms.title = f"Gate: {title}"
        gate_ms.save(update_fields=["title"])
    return phase


@transaction.atomic
def delete_waterfall_phase(project: Project, phase: WBSNode) -> None:
    assert_schedule_unlocked(project, fields={"structure"})
    if phase.project_id != project.id or not is_phase_node(phase):
        raise ValidationError({"detail": "Not a Waterfall phase on this project."})
    phase.delete()
    _reindex_phase_orders(project)
    _rebuild_phase_fs_links(project)
    _normalize_open_gates(project)
    from projects.services import recalculate_project_codes

    recalculate_project_codes(project)


def assert_phase_writable(node: WBSNode | None, *, allow_progress: bool = False) -> None:
    """Block work under a locked / not-yet-open phase."""
    del allow_progress  # reserved for future progress-only overrides
    phase = get_phase_ancestor(node)
    if phase is None:
        return
    if phase.gate_status == WBSNode.GateStatus.LOCKED:
        raise ValidationError(
            {
                "detail": (
                    f"Phase '{phase.title}' is locked. "
                    "Pass the previous phase gate before working here."
                ),
                "phase_id": phase.id,
                "gate_status": phase.gate_status,
            }
        )


def assert_schedule_unlocked(project: Project, *, fields: set[str] | None = None) -> None:
    """Block scope/schedule mutations while project.schedule_locked."""
    if not project.schedule_locked:
        return
    sensitive = fields or {
        "title",
        "description",
        "parent_id",
        "position",
        "node_type",
        "start_date",
        "end_date",
        "duration_days",
        "dependency",
        "structure",
    }
    raise ScheduleLockedError(
        {
            "detail": ScheduleLockedError.default_detail,
            "code": "schedule_locked",
            "fields": sorted(sensitive),
        }
    )


@transaction.atomic
def seed_waterfall_wbs(project: Project, *, replace: bool = False) -> list[WBSNode]:
    """Create classic SDLC L1 phases under root with FS links and gate milestones."""
    existing_phases = phase_queryset(project).exists()
    if existing_phases and not replace:
        raise ValidationError(
            {"detail": "Waterfall phases already exist. Pass replace=true to rebuild."}
        )
    if replace:
        assert_schedule_unlocked(project, fields={"structure"})

    if replace:
        project.wbs_nodes.exclude(parent__isnull=True).delete()
        phase_queryset(project).update(
            phase_key=None, phase_order=None, gate_status=None
        )

    root = project.wbs_nodes.filter(parent__isnull=True).first()
    if root is None:
        root = create_root_wbs_node(project)

    # Remove non-root children when seeding fresh (no prior phases)
    if not existing_phases or replace:
        project.wbs_nodes.exclude(pk=root.pk).delete()

    today = date.today()
    cursor = today
    phase_nodes: list[WBSNode] = []
    prev_activity: ScheduleActivity | None = None

    for order, (key, title, duration) in enumerate(WATERFALL_PHASES, start=1):
        phase = WBSNode.objects.create(
            project=project,
            parent=root,
            code=f"1.{order}",
            title=title,
            description=f"Waterfall phase: {title}",
            node_type=WBSNode.NodeType.DELIVERABLE,
            position=order - 1,
            phase_key=key,
            phase_order=order,
            gate_status=(
                WBSNode.GateStatus.OPEN
                if order == 1
                else WBSNode.GateStatus.LOCKED
            ),
            tracker=root.tracker,
            workflow_status=root.workflow_status,
        )
        phase_activity = ScheduleActivity.objects.create(
            wbs_node=phase,
            start_date=cursor,
            end_date=cursor + timedelta(days=duration),
            duration_days=duration,
            progress=0,
            is_milestone=False,
        )
        if prev_activity is not None:
            ActivityDependency.objects.create(
                predecessor=prev_activity,
                successor=phase_activity,
                dependency_type=ActivityDependency.DependencyType.FS,
                lag_days=0,
            )

        gate_ms = WBSNode.objects.create(
            project=project,
            parent=phase,
            code=f"1.{order}.1",
            title=f"Gate: {title}",
            description="Phase exit gate (go/no-go)",
            node_type=WBSNode.NodeType.MILESTONE,
            position=0,
            tracker=root.tracker,
            workflow_status=root.workflow_status,
        )
        ScheduleActivity.objects.create(
            wbs_node=gate_ms,
            start_date=cursor + timedelta(days=duration),
            end_date=cursor + timedelta(days=duration),
            duration_days=0,
            progress=0,
            is_milestone=True,
        )

        wp = WBSNode.objects.create(
            project=project,
            parent=phase,
            code=f"1.{order}.2",
            title=f"{title} work",
            description="",
            node_type=WBSNode.NodeType.WORK_PACKAGE,
            position=1,
            tracker=root.tracker,
            workflow_status=root.workflow_status,
        )
        ScheduleActivity.objects.create(
            wbs_node=wp,
            start_date=cursor,
            end_date=cursor + timedelta(days=max(duration - 1, 1)),
            duration_days=max(duration - 1, 1),
            progress=0,
            is_milestone=False,
        )

        phase_nodes.append(phase)
        prev_activity = phase_activity
        cursor = cursor + timedelta(days=duration + 1)

    if project.methodology != Project.Methodology.PREDICTIVE:
        # Keep user's choice; only default predictive when unset-like
        pass
    project.start_date = project.start_date or today
    project.end_date = cursor
    project.save(update_fields=["start_date", "end_date", "updated_at"])
    return phase_nodes


@transaction.atomic
def decide_phase_gate(
    project: Project,
    phase_node: WBSNode,
    *,
    decision: str,
    user,
    comment: str = "",
    checklist: list | None = None,
    create_baseline_on_pass: bool = True,
    lock_schedule_on_pass: bool = True,
) -> PhaseGate:
    if phase_node.project_id != project.id:
        raise ValidationError({"wbs_phase_node_id": "Phase must belong to project."})
    if not is_phase_node(phase_node):
        raise ValidationError({"wbs_phase_node_id": "Node is not a Waterfall phase."})
    if phase_node.gate_status == WBSNode.GateStatus.LOCKED:
        raise ValidationError(
            {"detail": "Phase is locked; previous gate must pass first."}
        )
    if phase_node.gate_status == WBSNode.GateStatus.PASSED:
        raise ValidationError({"detail": "Phase gate already passed."})

    decision = (decision or "").strip().lower()
    if decision not in PhaseGate.Decision.values:
        raise ValidationError({"decision": "Must be 'pass' or 'fail'."})

    items = checklist if checklist is not None else default_gate_checklist()
    if not isinstance(items, list):
        raise ValidationError({"checklist": "Expected a list."})

    baseline = None
    if decision == PhaseGate.Decision.PASS:
        phase_node.gate_status = WBSNode.GateStatus.PASSED
        phase_node.save(update_fields=["gate_status"])
        nxt = (
            phase_queryset(project)
            .filter(phase_order__gt=phase_node.phase_order or 0)
            .order_by("phase_order", "id")
            .first()
        )
        if nxt and nxt.gate_status == WBSNode.GateStatus.LOCKED:
            nxt.gate_status = WBSNode.GateStatus.OPEN
            nxt.save(update_fields=["gate_status"])
        if create_baseline_on_pass:
            baseline = create_baseline(
                project,
                f"Gate pass: {phase_node.title}"[:255],
                user,
            )
        if lock_schedule_on_pass:
            project.schedule_locked = True
            project.save(update_fields=["schedule_locked", "updated_at"])
    else:
        phase_node.gate_status = WBSNode.GateStatus.OPEN
        phase_node.save(update_fields=["gate_status"])

    gate = PhaseGate.objects.create(
        project=project,
        wbs_phase_node=phase_node,
        checklist=items,
        decision=decision,
        comment=str(comment or ""),
        decided_by=user,
        decided_at=timezone.now(),
        baseline=baseline,
    )
    return gate
