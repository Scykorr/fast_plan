"""PERT / network graph derived from schedule activities and FS dependencies."""

from __future__ import annotations

from datetime import timedelta
from math import sqrt
from random import Random

from projects.cpm import _activity_duration, compute_critical_path
from projects.models import ActivityDependency, ScheduleActivity

# Approximate normal z for one-sided percentiles
_Z_P10 = -1.28155156554
_Z_P50 = 0.0
_Z_P90 = 1.28155156554


def _pert_omp(most_likely: int) -> tuple[int, int, int]:
    optimistic = max(1, int(most_likely * 0.75))
    pessimistic = max(most_likely, int(round(most_likely * 1.5)))
    return optimistic, most_likely, pessimistic


def _sample_beta_pert(
    optimistic: int, most_likely: int, pessimistic: int, rng: Random
) -> float:
    """Sample duration from a PERT Beta distribution."""
    if pessimistic <= optimistic:
        return float(most_likely)
    mean = (optimistic + 4 * most_likely + pessimistic) / 6.0
    span = pessimistic - optimistic
    if span <= 0:
        return float(most_likely)
    mode_weight = (mean - optimistic) / span
    mode_weight = min(0.999, max(0.001, mode_weight))
    alpha = 1.0 + 4.0 * mode_weight
    beta = 1.0 + 4.0 * (1.0 - mode_weight)
    x = rng.gammavariate(alpha, 1.0)
    y = rng.gammavariate(beta, 1.0)
    t = x / (x + y) if (x + y) > 0 else rng.random()
    return optimistic + t * span


def _longest_path_days(
    node_days: dict[int, float],
    preds: dict[int, list[int]],
    node_ids: list[int],
) -> float:
    memo: dict[int, float] = {}

    def dfs(nid: int) -> float:
        if nid in memo:
            return memo[nid]
        parents = preds.get(nid) or []
        if not parents:
            memo[nid] = node_days.get(nid, 0.0)
        else:
            memo[nid] = node_days.get(nid, 0.0) + max(dfs(p) for p in parents)
        return memo[nid]

    if not node_ids:
        return 0.0
    return max(dfs(n) for n in node_ids)


def _finish_payload(
    *,
    p10: float,
    p50: float,
    p90: float,
    mean: float,
    sigma: float,
    method: str,
    project,
    trials: int | None = None,
) -> dict:
    finish = {
        "mean_days": round(mean, 2),
        "sigma_days": round(sigma, 2),
        "p10_days": round(max(0.0, p10), 2),
        "p50_days": round(max(0.0, p50), 2),
        "p90_days": round(max(0.0, p90), 2),
        "method": method,
    }
    if trials is not None:
        finish["trials"] = trials
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
    return finish


def _monte_carlo_finish(
    nodes: list[dict], preds: dict[int, list[int]], project, *, trials: int
) -> dict:
    if not nodes:
        return _finish_payload(
            p10=0,
            p50=0,
            p90=0,
            mean=0,
            sigma=0,
            method="monte_carlo",
            project=project,
            trials=trials,
        )
    rng = Random(42)
    node_ids = [n["id"] for n in nodes]
    samples: list[float] = []
    for _ in range(trials):
        durations = {
            n["id"]: _sample_beta_pert(
                n["optimistic_days"],
                n["most_likely_days"],
                n["pessimistic_days"],
                rng,
            )
            for n in nodes
        }
        samples.append(_longest_path_days(durations, preds, node_ids))
    samples.sort()

    def pct(p: float) -> float:
        idx = min(
            len(samples) - 1,
            max(0, int(round((p / 100.0) * (len(samples) - 1)))),
        )
        return samples[idx]

    mean = sum(samples) / len(samples)
    var = sum((s - mean) ** 2 for s in samples) / len(samples)
    return _finish_payload(
        p10=pct(10),
        p50=pct(50),
        p90=pct(90),
        mean=mean,
        sigma=sqrt(var),
        method="monte_carlo",
        project=project,
        trials=trials,
    )


def compute_pert_network(project, *, method: str = "normal", trials: int = 2000) -> dict:
    """Return nodes/edges plus finish percentiles (normal approx or Monte Carlo)."""
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
        optimistic, most_likely, pessimistic = _pert_omp(most_likely)
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
    preds: dict[int, list[int]] = {n["id"]: [] for n in nodes}
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
        if dep.dependency_type == ActivityDependency.DependencyType.FS:
            preds.setdefault(dep.successor_id, []).append(dep.predecessor_id)

    method_key = (method or "normal").strip().lower()
    if method_key in ("monte_carlo", "mc", "monte-carlo"):
        finish = _monte_carlo_finish(
            nodes,
            preds,
            project,
            trials=max(200, min(int(trials or 2000), 20000)),
        )
    else:
        critical_nodes = [n for n in nodes if n["is_critical"]]
        if critical_nodes:
            mu = sum(n["expected_days"] for n in critical_nodes)
            sigma = sqrt(sum(n["variance"] for n in critical_nodes))
        else:
            mu = float(cpm.get("project_duration") or 0)
            sigma = 0.0

        def _percentile(z: float) -> float:
            return max(0.0, mu + z * sigma)

        finish = _finish_payload(
            p10=_percentile(_Z_P10),
            p50=_percentile(_Z_P50),
            p90=_percentile(_Z_P90),
            mean=mu,
            sigma=sigma,
            method="critical_path_normal",
            project=project,
        )

    return {
        "nodes": nodes,
        "edges": edges,
        "project_duration": cpm.get("project_duration", 0),
        "critical_path_ids": cpm.get("critical_path_ids", []),
        "finish": finish,
    }
