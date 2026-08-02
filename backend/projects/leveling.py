"""Propose and apply schedule shifts for assignee overload (leveling lite)."""

from __future__ import annotations

from datetime import date, timedelta

from django.db import transaction
from django.utils import timezone

from projects.capacity_hints import activity_overlaps_week, assignee_week_loads, current_week_start
from projects.models import ActivityDependency, ScheduleActivity
from workspaces.search import _overlap_days


def _hours(
    *,
    start: date | None,
    end: date | None,
    progress: int,
    week_start: date,
    week_end: date,
) -> float:
    overlap = _overlap_days(start, end, week_start, week_end)
    if overlap <= 0:
        return 0.0
    remaining = max(0.0, 1.0 - (progress / 100))
    return round(overlap * 8 * remaining, 1)


def _fs_ok(
    activity_id: int,
    new_start: date,
    preds: dict[int, list[tuple[int, date | None, int]]],
) -> bool:
    for _pred_id, pred_end, lag in preds.get(activity_id, []):
        if pred_end is None:
            continue
        earliest = pred_end + timedelta(days=max(lag, 0) + 1)
        if new_start < earliest:
            return False
    return True


def _allocated(
    activities: list[ScheduleActivity],
    overrides: dict[int, tuple[date, date]],
    user_id: int,
    week_start: date,
    week_end: date,
) -> float:
    total = 0.0
    for act in activities:
        if act.wbs_node.assignee_id != user_id:
            continue
        start, end = overrides[act.id]
        total += _hours(
            start=start,
            end=end,
            progress=act.progress,
            week_start=week_start,
            week_end=week_end,
        )
    return round(total, 1)


def propose_leveling(
    project,
    *,
    week_start: date | None = None,
    max_shift_days: int = 14,
    assignee_id: int | None = None,
    max_proposals_per_assignee: int = 5,
) -> dict:
    """Read-only proposals. Apply via apply_leveling_proposals or PATCH activities."""
    week_start = week_start or current_week_start()
    week_end = week_start + timedelta(days=6)
    max_shift_days = max(1, min(int(max_shift_days or 14), 60))

    loads = assignee_week_loads(project.workspace, week_start=week_start)
    overloaded = [
        {
            "assignee_id": uid,
            "utilization_before": row["utilization"],
            "capacity_hours": row["capacity_hours"],
            "allocated_hours": row["allocated_hours"],
        }
        for uid, row in loads.items()
        if row.get("overloaded") and (assignee_id is None or uid == int(assignee_id))
    ]

    activities = list(
        ScheduleActivity.objects.filter(
            wbs_node__project=project,
            wbs_node__assignee__isnull=False,
            progress__lt=100,
            start_date__isnull=False,
            end_date__isnull=False,
        ).select_related("wbs_node", "wbs_node__assignee")
    )

    overrides: dict[int, tuple[date, date]] = {
        a.id: (a.start_date, a.end_date)  # type: ignore[misc]
        for a in activities
    }

    preds: dict[int, list[tuple[int, date | None, int]]] = {a.id: [] for a in activities}
    for dep in ActivityDependency.objects.filter(
        predecessor__wbs_node__project=project,
        successor__wbs_node__project=project,
        dependency_type=ActivityDependency.DependencyType.FS,
    ):
        if dep.successor_id not in preds:
            continue
        pred_end = overrides.get(dep.predecessor_id, (None, None))[1]
        preds[dep.successor_id].append((dep.predecessor_id, pred_end, dep.lag_days))

    proposals: list[dict] = []
    unresolved: list[dict] = []

    for row in overloaded:
        uid = int(row["assignee_id"])
        capacity = float(row["capacity_hours"] or 0)
        if capacity <= 0:
            unresolved.append({"assignee_id": uid, "detail": "Capacity hours is zero"})
            continue

        count = 0
        while (
            _allocated(activities, overrides, uid, week_start, week_end) > capacity
            and count < max_proposals_per_assignee
        ):
            candidates = [
                a
                for a in activities
                if a.wbs_node.assignee_id == uid
                and activity_overlaps_week(
                    type(
                        "T",
                        (),
                        {
                            "start_date": overrides[a.id][0],
                            "end_date": overrides[a.id][1],
                        },
                    )(),
                    week_start,
                    week_end,
                )
                and a.id not in {p["activity_id"] for p in proposals if p["assignee_id"] == uid}
            ]
            candidates.sort(
                key=lambda a: (
                    -_hours(
                        start=overrides[a.id][0],
                        end=overrides[a.id][1],
                        progress=a.progress,
                        week_start=week_start,
                        week_end=week_end,
                    ),
                    overrides[a.id][0],
                    -a.id,
                )
            )
            if not candidates:
                break

            placed = False
            before = _allocated(activities, overrides, uid, week_start, week_end)
            for activity in candidates:
                cur_start, cur_end = overrides[activity.id]
                duration = max(activity.duration_days or 1, (cur_end - cur_start).days + 1)
                live_preds = {
                    aid: [
                        (pid, overrides.get(pid, (None, None))[1], lag)
                        for pid, _old_end, lag in plist
                    ]
                    for aid, plist in preds.items()
                }
                for shift in range(1, max_shift_days + 1):
                    new_start = cur_start + timedelta(days=shift)
                    new_end = new_start + timedelta(days=duration - 1)
                    if not _fs_ok(activity.id, new_start, live_preds):
                        continue
                    trial = dict(overrides)
                    trial[activity.id] = (new_start, new_end)
                    after = _allocated(activities, trial, uid, week_start, week_end)
                    if after >= before:
                        continue
                    overrides[activity.id] = (new_start, new_end)
                    proposals.append(
                        {
                            "activity_id": activity.id,
                            "wbs_id": activity.wbs_node_id,
                            "code": activity.wbs_node.code,
                            "name": activity.wbs_node.title,
                            "assignee_id": uid,
                            "current": {
                                "start_date": cur_start.isoformat(),
                                "end_date": cur_end.isoformat(),
                                "duration_days": duration,
                            },
                            "proposed": {
                                "start_date": new_start.isoformat(),
                                "end_date": new_end.isoformat(),
                                "duration_days": duration,
                            },
                            "shift_days": shift,
                            "reason": (
                                f"Сдвиг на {shift} дн. из перегруженной недели "
                                f"{week_start.isoformat()}"
                            ),
                        }
                    )
                    count += 1
                    placed = True
                    break
                if placed:
                    break
            if not placed:
                break

        if _allocated(activities, overrides, uid, week_start, week_end) > capacity:
            unresolved.append(
                {
                    "assignee_id": uid,
                    "detail": "Cannot fully resolve within max_shift_days",
                }
            )

    return {
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat(),
        "overloaded_assignees": overloaded,
        "proposals": proposals,
        "unresolved": unresolved,
    }


def apply_leveling_proposals(project, proposals: list[dict]) -> dict:
    """
    Apply proposed date shifts. Returns undo payload with before/after snapshots.
    """
    if not proposals:
        return {
            "applied": [],
            "undo_token": None,
            "batch": {"created_at": timezone.now().isoformat(), "items": []},
        }

    applied: list[dict] = []
    undo_items: list[dict] = []

    with transaction.atomic():
        for raw in proposals:
            activity_id = int(raw["activity_id"])
            activity = (
                ScheduleActivity.objects.select_related("wbs_node")
                .filter(pk=activity_id, wbs_node__project=project)
                .first()
            )
            if activity is None:
                continue
            proposed = raw.get("proposed") or {}
            try:
                new_start = date.fromisoformat(str(proposed["start_date"])[:10])
                new_end = date.fromisoformat(str(proposed["end_date"])[:10])
            except (KeyError, TypeError, ValueError):
                continue
            duration = int(proposed.get("duration_days") or activity.duration_days or 1)
            before = {
                "start_date": activity.start_date.isoformat() if activity.start_date else None,
                "end_date": activity.end_date.isoformat() if activity.end_date else None,
                "duration_days": activity.duration_days,
            }
            activity.start_date = new_start
            activity.end_date = new_end
            activity.duration_days = max(1, duration)
            activity.save(update_fields=["start_date", "end_date", "duration_days"])
            after = {
                "start_date": new_start.isoformat(),
                "end_date": new_end.isoformat(),
                "duration_days": activity.duration_days,
            }
            applied.append({"activity_id": activity_id, "before": before, "after": after})
            undo_items.append({"activity_id": activity_id, **before})

    batch = {
        "created_at": timezone.now().isoformat(),
        "project_id": project.id,
        "items": undo_items,
    }
    return {
        "applied": applied,
        "undo_token": f"leveling-{project.id}-{batch['created_at']}",
        "batch": batch,
    }


def undo_leveling_batch(project, items: list[dict]) -> dict:
    """Restore dates from an apply batch `items` list."""
    restored: list[dict] = []
    with transaction.atomic():
        for raw in items:
            activity_id = int(raw["activity_id"])
            activity = ScheduleActivity.objects.filter(
                pk=activity_id, wbs_node__project=project
            ).first()
            if activity is None:
                continue
            start_raw = raw.get("start_date")
            end_raw = raw.get("end_date")
            if not start_raw or not end_raw:
                continue
            activity.start_date = date.fromisoformat(str(start_raw)[:10])
            activity.end_date = date.fromisoformat(str(end_raw)[:10])
            if raw.get("duration_days") is not None:
                activity.duration_days = max(1, int(raw["duration_days"]))
            activity.save(update_fields=["start_date", "end_date", "duration_days"])
            restored.append({"activity_id": activity_id})
    return {"restored": restored, "count": len(restored)}
