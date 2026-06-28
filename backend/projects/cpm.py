from datetime import date

from projects.models import ActivityDependency, ScheduleActivity


def _activity_duration(activity: ScheduleActivity) -> int:
    if activity.duration_days:
        return activity.duration_days
    if activity.start_date and activity.end_date:
        return max((activity.end_date - activity.start_date).days, 1)
    return 1


def compute_critical_path(project) -> dict:
    activities = list(
        ScheduleActivity.objects.filter(wbs_node__project=project)
        .select_related("wbs_node")
        .order_by("id")
    )
    if not activities:
        return {"activities": [], "critical_path_ids": [], "project_duration": 0}

    deps = ActivityDependency.objects.filter(
        predecessor__wbs_node__project=project,
        successor__wbs_node__project=project,
        dependency_type=ActivityDependency.DependencyType.FS,
    )

    predecessors: dict[int, list[tuple[int, int]]] = {a.id: [] for a in activities}
    successors: dict[int, list[int]] = {a.id: [] for a in activities}
    for dep in deps:
        predecessors[dep.successor_id].append((dep.predecessor_id, dep.lag_days))
        successors[dep.predecessor_id].append(dep.successor_id)

    es: dict[int, int] = {}
    ef: dict[int, int] = {}
    for activity in _topological_sort(activities, predecessors):
        duration = _activity_duration(activity)
        if predecessors[activity.id]:
            es[activity.id] = max(
                ef[pred_id] + lag for pred_id, lag in predecessors[activity.id]
            )
        else:
            es[activity.id] = 0
        ef[activity.id] = es[activity.id] + duration

    project_duration = max(ef.values()) if ef else 0
    ls: dict[int, int] = {}
    lf: dict[int, int] = {}
    for activity in reversed(_topological_sort(activities, predecessors)):
        duration = _activity_duration(activity)
        if successors[activity.id]:
            lf[activity.id] = min(ls[succ_id] for succ_id in successors[activity.id])
        else:
            lf[activity.id] = project_duration
        ls[activity.id] = lf[activity.id] - duration

    result_activities = []
    critical_ids = []
    for activity in activities:
        slack = ls[activity.id] - es[activity.id]
        is_critical = slack == 0 and project_duration > 0
        if is_critical:
            critical_ids.append(activity.id)
        result_activities.append(
            {
                "id": activity.id,
                "wbs_id": activity.wbs_node_id,
                "code": activity.wbs_node.code,
                "name": activity.wbs_node.title,
                "duration_days": _activity_duration(activity),
                "early_start": es[activity.id],
                "early_finish": ef[activity.id],
                "late_start": ls[activity.id],
                "late_finish": lf[activity.id],
                "slack": slack,
                "is_critical": is_critical,
            }
        )

    return {
        "activities": result_activities,
        "critical_path_ids": critical_ids,
        "project_duration": project_duration,
    }


def _topological_sort(activities, predecessors):
    incoming = {a.id: len(predecessors[a.id]) for a in activities}
    queue = [a for a in activities if incoming[a.id] == 0]
    ordered = []
    while queue:
        activity = queue.pop(0)
        ordered.append(activity)
        for other in activities:
            if any(pred_id == activity.id for pred_id, _ in predecessors[other.id]):
                incoming[other.id] -= 1
                if incoming[other.id] == 0:
                    queue.append(other)
    if len(ordered) != len(activities):
        return activities
    return ordered


def compute_evm_lite(project, activities, actual_cost: float = 0) -> dict:
    budget = float(project.budget or 0)
    if not activities or budget <= 0:
        return {
            "budget": budget,
            "earned_value": 0,
            "planned_value": 0,
            "actual_cost": actual_cost,
            "cpi": None,
            "spi": None,
            "percent_complete": 0,
        }

    percent_complete = round(sum(a.progress for a in activities) / len(activities))
    earned_value = round(budget * percent_complete / 100, 2)

    today = date.today()
    planned_progress = 0
    schedulable = [a for a in activities if a.start_date and a.end_date]
    if schedulable:
        planned_progress = sum(
            _planned_percent(a, today) for a in schedulable
        ) / len(schedulable)
    planned_value = round(budget * planned_progress / 100, 2)

    cpi = round(earned_value / actual_cost, 2) if actual_cost > 0 else None
    spi = round(earned_value / planned_value, 2) if planned_value > 0 else None

    return {
        "budget": budget,
        "earned_value": earned_value,
        "planned_value": planned_value,
        "actual_cost": actual_cost,
        "cpi": cpi,
        "spi": spi,
        "percent_complete": percent_complete,
    }


def _planned_percent(activity: ScheduleActivity, today: date) -> int:
    start = activity.start_date
    end = activity.end_date
    if today <= start:
        return 0
    if today >= end:
        return 100
    total_days = max((end - start).days, 1)
    elapsed = (today - start).days
    return min(round(elapsed / total_days * 100), 100)
