from datetime import date, timedelta

from django.db import transaction

from kanban.models import Board, Card, Column
from projects.models import Project, ScheduleActivity, WBSNode

DEFAULT_PROJECT_COLUMNS = ("К выполнению", "В работе", "Готово")


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
    return WBSNode.objects.create(
        project=project,
        parent=None,
        code="1",
        title=project.name,
        node_type=WBSNode.NodeType.DELIVERABLE,
        position=0,
    )


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
    node = WBSNode.objects.create(
        project=project,
        parent=parent,
        code=code,
        title=title,
        node_type=node_type,
        position=parent.children.count(),
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
