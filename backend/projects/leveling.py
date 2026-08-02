"""Propose schedule shifts to relieve assignee weekly overload (leveling lite)."""

from __future__ import annotations

from datetime import date, timedelta

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
    """
    Read-only proposals: shift incomplete activities out of an overloaded week.
    Apply via PATCH /api/activities/<id>/ — this function never writes.
    """
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

    # predecessor_id, predecessor_end (live via overrides), lag
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
                # refresh pred ends from current overrides
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
