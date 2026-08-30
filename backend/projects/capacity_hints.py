"""Capacity-aware schedule hints for Gantt/WBS (P10 sprint 3)."""

from __future__ import annotations

from datetime import date, timedelta

from workspaces.search import _overlap_days, build_capacity_report


def current_week_start(today: date | None = None) -> date:
    day = today or date.today()
    return day - timedelta(days=day.weekday())


def assignee_week_loads(workspace, *, week_start: date | None = None) -> dict[int, dict]:
    """Map user_id → capacity row for the given week (reuse capacity report math)."""
    report = build_capacity_report(workspace, week_start=week_start)
    loads: dict[int, dict] = {}
    for member in report["members"]:
        utilization = member.get("utilization")
        loads[member["user_id"]] = {
            "week_start": report["week_start"],
            "week_end": report["week_end"],
            "capacity_hours": member["capacity_hours"],
            "allocated_hours": member["allocated_hours"],
            "utilization": utilization,
            "overloaded": bool(utilization is not None and utilization > 1.0),
        }
    return loads


def capacity_hint_for_assignee(loads: dict[int, dict], assignee_id: int | None) -> dict | None:
    if not assignee_id:
        return None
    row = loads.get(int(assignee_id))
    if row is None:
        return None
    return {
        "week_start": row["week_start"],
        "week_end": row["week_end"],
        "capacity_hours": row["capacity_hours"],
        "allocated_hours": row["allocated_hours"],
        "utilization": row["utilization"],
        "overloaded": row["overloaded"],
        "hint": (
            f"Перегруз {row['utilization']:.0%} на неделе {row['week_start']}"
            if row["overloaded"]
            else None
        ),
    }


def activity_overlaps_week(activity, week_start: date, week_end: date) -> bool:
    return _overlap_days(activity.start_date, activity.end_date, week_start, week_end) > 0
