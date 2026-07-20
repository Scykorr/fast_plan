"""PERT / network graph derived from schedule activities and FS dependencies."""

from projects.cpm import _activity_duration, compute_critical_path
from projects.models import ActivityDependency, ScheduleActivity


def compute_pert_network(project) -> dict:
    """Return nodes/edges for a network diagram plus PERT expected durations.

    For each activity:
    - optimistic = max(1, floor(duration * 0.75))
    - most_likely = duration
    - pessimistic = ceil(duration * 1.5)
    - expected = (O + 4M + P) / 6
    """
    cpm = compute_critical_path(project)
    activities = list(
        ScheduleActivity.objects.filter(wbs_node__project=project)
        .select_related("wbs_node")
        .order_by("id")
    )
    critical_ids = set(cpm.get("critical_path_ids") or [])
    cpm_by_id = {item["id"]: item for item in cpm.get("activities") or []}

    nodes = []
    for activity in activities:
        most_likely = _activity_duration(activity)
        optimistic = max(1, int(most_likely * 0.75))
        pessimistic = max(most_likely, int(round(most_likely * 1.5)))
        expected = round((optimistic + 4 * most_likely + pessimistic) / 6, 2)
        cpm_row = cpm_by_id.get(activity.id, {})
        nodes.append(
            {
                "id": activity.id,
                "wbs_id": activity.wbs_node_id,
                "code": activity.wbs_node.code,
                "name": activity.wbs_node.title,
                "optimistic_days": optimistic,
                "most_likely_days": most_likely,
                "pessimistic_days": pessimistic,
                "expected_days": expected,
                "early_start": cpm_row.get("early_start"),
                "early_finish": cpm_row.get("early_finish"),
                "late_start": cpm_row.get("late_start"),
                "late_finish": cpm_row.get("late_finish"),
                "slack": cpm_row.get("slack"),
                "is_critical": activity.id in critical_ids,
            }
        )

    edges = []
    deps = ActivityDependency.objects.filter(
        predecessor__wbs_node__project=project,
        successor__wbs_node__project=project,
    ).select_related("predecessor", "successor")
    for dep in deps:
        edges.append(
            {
                "id": dep.id,
                "from": dep.predecessor_id,
                "to": dep.successor_id,
                "type": dep.dependency_type,
                "lag_days": dep.lag_days,
            }
        )

    return {
        "nodes": nodes,
        "edges": edges,
        "project_duration": cpm.get("project_duration", 0),
        "critical_path_ids": cpm.get("critical_path_ids", []),
    }
