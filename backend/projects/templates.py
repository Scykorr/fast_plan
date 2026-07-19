from django.db import transaction

from kanban.models import Column
from projects.models import ProjectTemplate, ScheduleActivity, WBSNode
from tracking.models import IssueStatus, Tracker


def capture_project_template(project, *, name, description, created_by):
    nodes = project.wbs_nodes.select_related(
        "parent",
        "tracker",
        "workflow_status",
        "schedule",
    ).order_by("code")
    structure = {
        "project_tracker": project.tracker.name if project.tracker else None,
        "columns": list(
            project.board.columns.order_by("position").values_list("title", flat=True)
        ),
        "wbs": [
            {
                "code": node.code,
                "parent_code": node.parent.code if node.parent else None,
                "title": node.title if node.parent else "{{ project_name }}",
                "description": node.description,
                "node_type": node.node_type,
                "position": node.position,
                "tracker": node.tracker.name if node.tracker else None,
                "workflow_status": (
                    node.workflow_status.name if node.workflow_status else None
                ),
                "schedule": (
                    {
                        "duration_days": node.schedule.duration_days,
                        "is_milestone": node.schedule.is_milestone,
                    }
                    if hasattr(node, "schedule")
                    else None
                ),
            }
            for node in nodes
        ],
    }
    return ProjectTemplate.objects.create(
        workspace=project.workspace,
        name=name,
        description=description,
        structure=structure,
        created_by=created_by,
    )


@transaction.atomic
def apply_project_template(project, template):
    if template.workspace_id != project.workspace_id:
        raise ValueError("Template belongs to a different workspace.")
    structure = template.structure or {}
    tracker_name = structure.get("project_tracker")
    if tracker_name:
        tracker = Tracker.objects.filter(
            workspace=project.workspace,
            name=tracker_name,
        ).first()
        if tracker:
            project.tracker = tracker
            project.save(update_fields=["tracker"])

    board = project.board
    board.columns.all().delete()
    for position, title in enumerate(structure.get("columns") or []):
        Column.objects.create(board=board, title=title, position=position)
    if not board.columns.exists():
        for position, title in enumerate(("К выполнению", "В работе", "Готово")):
            Column.objects.create(board=board, title=title, position=position)

    project.wbs_nodes.all().delete()
    created_by_code = {}
    for item in structure.get("wbs") or []:
        tracker = (
            Tracker.objects.filter(
                workspace=project.workspace,
                name=item.get("tracker"),
            ).first()
            if item.get("tracker")
            else None
        )
        workflow_status = (
            IssueStatus.objects.filter(
                workspace=project.workspace,
                name=item.get("workflow_status"),
            ).first()
            if item.get("workflow_status")
            else None
        )
        parent = created_by_code.get(item.get("parent_code"))
        node = WBSNode.objects.create(
            project=project,
            parent=parent,
            code=item["code"],
            title=item.get("title", "").replace("{{ project_name }}", project.name),
            description=item.get("description", ""),
            node_type=item.get("node_type", WBSNode.NodeType.WORK_PACKAGE),
            position=item.get("position", 0),
            tracker=tracker,
            workflow_status=workflow_status,
        )
        created_by_code[node.code] = node
        schedule = item.get("schedule")
        if schedule:
            ScheduleActivity.objects.create(
                wbs_node=node,
                duration_days=schedule.get("duration_days", 1),
                is_milestone=schedule.get("is_milestone", False),
            )

    if not project.wbs_nodes.exists():
        from projects.services import create_root_wbs_node

        create_root_wbs_node(project)
