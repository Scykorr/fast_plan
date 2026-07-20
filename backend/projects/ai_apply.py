"""Apply AI-generated WBS/schedule drafts to a project."""

from __future__ import annotations

from datetime import date, timedelta

from django.db import transaction

from projects.models import ActivityDependency, ScheduleActivity, WBSNode
from projects.services import create_work_package


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(str(value).strip())


@transaction.atomic
def apply_wbs_draft(project, nodes: list[dict], dependencies: list[dict] | None = None) -> dict:
    root = project.wbs_nodes.filter(parent__isnull=True).order_by("id").first()
    if root is None:
        raise ValueError("Project has no root WBS node.")

    by_code: dict[str, WBSNode] = {root.code: root}
    created = 0
    updated = 0
    errors: list[str] = []

    sorted_nodes = sorted(nodes, key=lambda item: str(item.get("code", "")).count("."))
    for index, item in enumerate(sorted_nodes, start=1):
        code = str(item.get("code", "")).strip()
        title = str(item.get("title", "")).strip()
        if not code or not title:
            errors.append(f"Node {index}: code and title are required.")
            continue
        if code == root.code:
            root.title = title
            root.save(update_fields=["title"])
            updated += 1
            continue

        parent_code = str(item.get("parent_code") or root.code).strip()
        parent = by_code.get(parent_code) or project.wbs_nodes.filter(code=parent_code).first()
        if parent is None:
            errors.append(f"Node {index}: parent code {parent_code} not found for {code}.")
            continue

        node_type = str(item.get("node_type") or WBSNode.NodeType.WORK_PACKAGE).strip()
        if node_type not in WBSNode.NodeType.values:
            node_type = WBSNode.NodeType.WORK_PACKAGE

        node = project.wbs_nodes.filter(code=code).first()
        if node is None:
            node = create_work_package(
                project,
                parent,
                title,
                node_type,
                with_schedule=True,
                with_kanban_card=node_type == WBSNode.NodeType.WORK_PACKAGE,
            )
            if node.code != code:
                node.code = code
                node.save(update_fields=["code"])
            created += 1
        else:
            node.title = title
            node.node_type = node_type
            node.parent = parent
            node.save(update_fields=["title", "node_type", "parent"])
            updated += 1

        by_code[code] = node

        schedule, _ = ScheduleActivity.objects.get_or_create(
            wbs_node=node,
            defaults={
                "duration_days": 1,
                "progress": 0,
                "is_milestone": node_type == WBSNode.NodeType.MILESTONE,
            },
        )
        duration_raw = item.get("duration_days")
        start = _parse_date(item.get("start_date"))
        end = _parse_date(item.get("end_date"))
        if duration_raw is not None:
            try:
                schedule.duration_days = max(1, int(duration_raw))
            except (TypeError, ValueError):
                errors.append(f"Node {index}: invalid duration_days.")
        if start:
            schedule.start_date = start
        if end:
            schedule.end_date = end
        elif start and schedule.duration_days:
            schedule.end_date = start + timedelta(days=max(schedule.duration_days - 1, 0))
        if start and schedule.end_date and schedule.end_date >= start:
            schedule.duration_days = max((schedule.end_date - start).days + 1, 1)
        schedule.is_milestone = node_type == WBSNode.NodeType.MILESTONE
        schedule.save()

    dependencies_created = 0
    for index, item in enumerate(dependencies or [], start=1):
        pred_code = str(item.get("predecessor_code", "")).strip()
        succ_code = str(item.get("successor_code", "")).strip()
        if not pred_code or not succ_code:
            errors.append(f"Dependency {index}: predecessor_code and successor_code required.")
            continue
        predecessor = ScheduleActivity.objects.filter(
            wbs_node__project=project,
            wbs_node__code=pred_code,
        ).first()
        successor = ScheduleActivity.objects.filter(
            wbs_node__project=project,
            wbs_node__code=succ_code,
        ).first()
        if predecessor is None or successor is None:
            errors.append(
                f"Dependency {index}: schedule not found for {pred_code} → {succ_code}."
            )
            continue
        dep_type = str(item.get("dependency_type") or ActivityDependency.DependencyType.FS)
        if dep_type not in ActivityDependency.DependencyType.values:
            dep_type = ActivityDependency.DependencyType.FS
        lag_days = int(item.get("lag_days") or 0)
        _, created_flag = ActivityDependency.objects.get_or_create(
            predecessor=predecessor,
            successor=successor,
            defaults={"dependency_type": dep_type, "lag_days": lag_days},
        )
        if created_flag:
            dependencies_created += 1

    return {
        "created": created,
        "updated": updated,
        "dependencies_created": dependencies_created,
        "errors": errors,
    }
