from datetime import date, timedelta

from django.core.exceptions import ValidationError
from django.db import transaction

from kanban.models import Board, Card, Column
from projects.models import Project, ScheduleActivity, WBSNode
from tracking.models import IssueStatus, Tracker
from tracking.services import serialize_custom_values

DEFAULT_PROJECT_COLUMNS = ("К выполнению", "В работе", "Готово")


def _default_project_tracker(workspace):
    return (
        Tracker.objects.filter(
            workspace=workspace,
            target=Tracker.Target.PROJECT,
            is_default=True,
        ).first()
        or Tracker.objects.filter(
            workspace=workspace, target=Tracker.Target.PROJECT
        ).first()
    )


def _default_issue_tracker(workspace):
    return (
        Tracker.objects.filter(
            workspace=workspace,
            target=Tracker.Target.ISSUE,
            is_default=True,
        ).first()
        or Tracker.objects.filter(workspace=workspace, target=Tracker.Target.ISSUE).first()
    )


def _default_workflow_status(workspace):
    return (
        IssueStatus.objects.filter(workspace=workspace, is_default=True).first()
        or IssueStatus.objects.filter(workspace=workspace).first()
    )


def generate_wbs_code(project: Project, parent: WBSNode | None) -> str:
    if parent is None:
        return "1"
    sibling_count = parent.children.count() + 1
    return f"{parent.code}.{sibling_count}"


def create_project_board(project: Project) -> Board:
    board = Board.objects.create(
        workspace=project.workspace,
        project=project,
        title=f"Проект: {project.name}",
        position=project.workspace.boards.count(),
    )
    for index, title in enumerate(DEFAULT_PROJECT_COLUMNS):
        Column.objects.create(board=board, title=title, position=index)
    return board


def create_root_wbs_node(project: Project) -> WBSNode:
    workspace = project.workspace
    return WBSNode.objects.create(
        project=project,
        parent=None,
        code="1",
        title=project.name,
        node_type=WBSNode.NodeType.DELIVERABLE,
        position=0,
        tracker=_default_project_tracker(workspace),
        workflow_status=_default_workflow_status(workspace),
    )


def _collect_descendant_ids(node: WBSNode) -> set[int]:
    ids: set[int] = set()
    for child in node.children.all():
        ids.add(child.id)
        ids.update(_collect_descendant_ids(child))
    return ids


def _reorder_siblings(parent_id: int | None, project: Project) -> None:
    siblings = list(
        WBSNode.objects.filter(parent_id=parent_id, project=project).order_by(
            "position", "id"
        )
    )
    for index, sibling in enumerate(siblings):
        if sibling.position != index:
            WBSNode.objects.filter(pk=sibling.pk).update(position=index)


def recalculate_project_codes(project: Project) -> None:
    nodes = list(project.wbs_nodes.all())
    for node in nodes:
        WBSNode.objects.filter(pk=node.pk).update(code=f"__tmp_{node.pk}__")

    def assign_codes(parent: WBSNode | None, children: list[WBSNode]) -> None:
        for index, child in enumerate(children, start=1):
            code = str(index) if parent is None else f"{parent.code}.{index}"
            WBSNode.objects.filter(pk=child.pk).update(code=code)
            child.code = code
            grandchildren = list(child.children.order_by("position", "id"))
            assign_codes(child, grandchildren)

    roots = list(project.wbs_nodes.filter(parent__isnull=True).order_by("position", "id"))
    assign_codes(None, roots)


@transaction.atomic
def move_wbs_node(node: WBSNode, *, parent_id: int, position: int) -> WBSNode:
    if node.parent_id is None:
        raise ValidationError("Root WBS node cannot be moved.")

    if parent_id == node.id:
        raise ValidationError("Cannot move node into itself.")

    descendant_ids = _collect_descendant_ids(node)
    if parent_id in descendant_ids:
        raise ValidationError("Cannot move node into its descendant.")

    parent = WBSNode.objects.get(pk=parent_id, project=node.project)
    old_parent_id = node.parent_id
    structure_changed = parent_id != old_parent_id

    siblings = list(
        WBSNode.objects.filter(parent_id=parent_id, project=node.project)
        .exclude(pk=node.pk)
        .order_by("position", "id")
    )
    position = min(max(position, 0), len(siblings))
    siblings.insert(position, node)

    node.parent_id = parent_id
    node.save(update_fields=["parent_id"])

    for index, sibling in enumerate(siblings):
        if sibling.position != index:
            WBSNode.objects.filter(pk=sibling.pk).update(position=index)

    if structure_changed:
        _reorder_siblings(old_parent_id, node.project)
        recalculate_project_codes(node.project)

    node.refresh_from_db()
    return node


@transaction.atomic
def create_work_package(
    project: Project,
    parent: WBSNode,
    title: str,
    node_type: str = WBSNode.NodeType.WORK_PACKAGE,
    *,
    with_schedule: bool = True,
    with_kanban_card: bool = True,
) -> WBSNode:
    code = generate_wbs_code(project, parent)
    workspace = project.workspace
    node = WBSNode.objects.create(
        project=project,
        parent=parent,
        code=code,
        title=title,
        node_type=node_type,
        position=parent.children.count(),
        tracker=_default_issue_tracker(workspace),
        workflow_status=_default_workflow_status(workspace),
    )

    if with_schedule:
        today = date.today()
        ScheduleActivity.objects.create(
            wbs_node=node,
            start_date=today,
            end_date=today + timedelta(days=7),
            duration_days=7,
            progress=0,
            is_milestone=node_type == WBSNode.NodeType.MILESTONE,
        )

    if with_kanban_card and node_type == WBSNode.NodeType.WORK_PACKAGE:
        board = getattr(project, "board", None)
        if board is None:
            board = create_project_board(project)
        first_column = board.columns.order_by("position", "id").first()
        if first_column:
            Card.objects.create(
                column=first_column,
                wbs_node=node,
                title=title,
                position=first_column.cards.count(),
            )

    return node


def build_wbs_tree(nodes: list[WBSNode]) -> list[dict]:
    by_parent: dict[int | None, list[WBSNode]] = {}
    for node in nodes:
        by_parent.setdefault(node.parent_id, []).append(node)

    def serialize_node(node: WBSNode) -> dict:
        schedule = getattr(node, "schedule", None)
        card = getattr(node, "card", None)
        return {
            "id": node.id,
            "code": node.code,
            "title": node.title,
            "description": node.description,
            "node_type": node.node_type,
            "position": node.position,
            "parent_id": node.parent_id,
            "tracker_id": node.tracker_id,
            "tracker_name": node.tracker.name if node.tracker else None,
            "workflow_status_id": node.workflow_status_id,
            "workflow_status_name": (
                node.workflow_status.name if node.workflow_status else None
            ),
            "assignee_id": node.assignee_id,
            "assignee_name": (
                node.assignee.get_username() if node.assignee else None
            ),
            "custom_values": serialize_custom_values(node),
            "schedule": (
                {
                    "id": schedule.id,
                    "start_date": schedule.start_date,
                    "end_date": schedule.end_date,
                    "duration_days": schedule.duration_days,
                    "progress": schedule.progress,
                    "is_milestone": schedule.is_milestone,
                }
                if schedule
                else None
            ),
            "card_id": card.id if card else None,
            "children": [
                serialize_node(child)
                for child in by_parent.get(node.id, [])
            ],
        }

    return [serialize_node(node) for node in by_parent.get(None, [])]
