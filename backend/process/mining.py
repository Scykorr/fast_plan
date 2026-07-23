"""Process mining lite (P8g) — DFG / paths / bottlenecks from ActivityInstance."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from process.models import ActivityInstance, ProcessInstance


def _node_id(activity: ActivityInstance) -> str:
    payload = activity.payload or {}
    bpmn_id = payload.get("bpmn_id") or ""
    if bpmn_id:
        return str(bpmn_id)
    return activity.task_name or activity.task_type or activity.task_id


def build_process_mining(workspace, *, limit_instances: int = 200) -> dict[str, Any]:
    """
    Build a lightweight process-mining snapshot (not Celonis-class mining).

    Uses ActivityInstance event log ordered by created_at per process instance.
    """
    instances = (
        ProcessInstance.objects.filter(workspace=workspace)
        .order_by("-started_at")[:limit_instances]
    )
    instance_ids = [i.id for i in instances]
    activities = (
        ActivityInstance.objects.filter(instance_id__in=instance_ids)
        .order_by("instance_id", "created_at", "id")
    )

    by_instance: dict[int, list[ActivityInstance]] = defaultdict(list)
    for act in activities:
        by_instance[act.instance_id].append(act)

    edge_counts: Counter[tuple[str, str]] = Counter()
    path_counts: Counter[tuple[str, ...]] = Counter()
    durations: dict[str, list[float]] = defaultdict(list)
    event_count = 0

    for inst_id, acts in by_instance.items():
        nodes = [_node_id(a) for a in acts]
        event_count += len(nodes)
        if nodes:
            path_counts[tuple(nodes)] += 1
        for i in range(len(nodes) - 1):
            edge_counts[(nodes[i], nodes[i + 1])] += 1
        for act in acts:
            if act.completed_at and act.created_at:
                hours = (act.completed_at - act.created_at).total_seconds() / 3600.0
                if hours >= 0:
                    durations[_node_id(act)].append(hours)

    dfg = [
        {"from": a, "to": b, "count": c}
        for (a, b), c in edge_counts.most_common(50)
    ]
    top_paths = [
        {"path": list(path), "count": count}
        for path, count in path_counts.most_common(20)
    ]
    bottlenecks = sorted(
        [
            {
                "node": node,
                "avg_hours": sum(vals) / len(vals),
                "samples": len(vals),
            }
            for node, vals in durations.items()
            if vals
        ],
        key=lambda row: row["avg_hours"],
        reverse=True,
    )[:20]

    return {
        "instance_sample": len(instance_ids),
        "event_count": event_count,
        "dfg": dfg,
        "top_paths": top_paths,
        "bottlenecks": bottlenecks,
    }
