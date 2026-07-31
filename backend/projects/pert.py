"""PERT / network graph derived from schedule activities and FS dependencies."""

from __future__ import annotations

from datetime import timedelta
from math import sqrt

from projects.cpm import _activity_duration, compute_critical_path
from projects.models import ActivityDependency, ScheduleActivity

# Approximate normal z for one-sided percentiles
_Z_P10 = -1.28155156554
_Z_P50 = 0.0
_Z_P90 = 1.28155156554


def compute_pert_network(project) -> dict:
    """Return nodes/edges for a network diagram plus PERT expected durations.

    For each activity:
    - optimistic = max(1, floor(duration * 0.75))
    - most_likely = duration
    - pessimistic = ceil(duration * 1.5)
    - expected = (O + 4M + P) / 6
    - variance = ((P - O) / 6) ** 2

    Project finish percentiles use critical-path Σ expected and √Σ variance
    under a normal approximation (P10 / P50 / P90).
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
        variance = ((pessimistic - optimistic) / 6) ** 2
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
                "variance": round(variance, 4),
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

    critical_nodes = [n for n in nodes if n["is_critical"]]
    if critical_nodes:
        mu = sum(n["expected_days"] for n in critical_nodes)
        sigma = sqrt(sum(n["variance"] for n in critical_nodes))
    else:
        mu = float(cpm.get("project_duration") or 0)
        sigma = 0.0

    def _percentile(z: float) -> float:
        return round(max(0.0, mu + z * sigma), 2)

    finish = {
        "mean_days": round(mu, 2),
        "sigma_days": round(sigma, 2),
        "p10_days": _percentile(_Z_P10),
        "p50_days": _percentile(_Z_P50),
        "p90_days": _percentile(_Z_P90),
        "method": "critical_path_normal",
    }
    start = getattr(project, "start_date", None)
    if start is not None:
        finish["start_date"] = start.isoformat()
        finish["p10_date"] = (
            start + timedelta(days=int(round(finish["p10_days"])))
        ).isoformat()
        finish["p50_date"] = (
            start + timedelta(days=int(round(finish["p50_days"])))
        ).isoformat()
        finish["p90_date"] = (
            start + timedelta(days=int(round(finish["p90_days"])))
        ).isoformat()

    return {
        "nodes": nodes,
        "edges": edges,
        "project_duration": cpm.get("project_duration", 0),
        "critical_path_ids": cpm.get("critical_path_ids", []),
        "finish": finish,
    }
