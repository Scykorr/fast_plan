"""Bind process UserTask to WBS/Kanban and sync on complete."""

from __future__ import annotations

from rest_framework.exceptions import ValidationError

from projects.models import ScheduleActivity, WBSNode
from projects.sync import sync_card_from_activity


def bind_user_task_to_wbs(user_task, wbs_node_id: int | None, workspace) -> None:
    if wbs_node_id in (None, ""):
        user_task.wbs_node = None
        user_task.save(update_fields=["wbs_node"])
        return

    node = WBSNode.objects.filter(
        pk=int(wbs_node_id), project__workspace=workspace
    ).select_related("project", "schedule").first()
    if node is None:
        raise ValidationError({"wbs_node_id": "WBS node not found."})

    if user_task.instance.project_id and node.project_id != user_task.instance.project_id:
        raise ValidationError(
            {"wbs_node_id": "WBS node must belong to the process instance project."}
        )

    user_task.wbs_node = node
    user_task.save(update_fields=["wbs_node"])


def complete_bound_wbs(user_task) -> None:
    """Mark bound WBS schedule as 100% and move Kanban card to last column."""
    node = user_task.wbs_node
    if node is None:
        return
    schedule = getattr(node, "schedule", None)
    if schedule is None:
        schedule = ScheduleActivity.objects.filter(wbs_node=node).first()
    if schedule is None:
        return
    schedule.progress = 100
    schedule.save(update_fields=["progress"])
    sync_card_from_activity(schedule)
