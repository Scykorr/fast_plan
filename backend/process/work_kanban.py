"""Kanban sync helpers for ProcessWorkNode (Process-as-WBS)."""

from __future__ import annotations

from kanban.models import Board, Card, Column
from process.models import ProcessInstance, ProcessWorkNode
from projects.sync import column_for_progress


def ensure_process_board(instance: ProcessInstance) -> Board:
    try:
        return instance.board
    except Board.DoesNotExist:
        pass
    board = Board.objects.create(
        workspace=instance.workspace,
        process_instance=instance,
        title=f"Process #{instance.id}",
        position=0,
    )
    for idx, title in enumerate(("To do", "Doing", "Done")):
        Column.objects.create(board=board, title=title, position=idx)
    return board


def ensure_card_for_work_node(node: ProcessWorkNode) -> Card | None:
    if node.node_type != ProcessWorkNode.NodeType.USER_TASK:
        return None
    try:
        return node.card
    except Card.DoesNotExist:
        pass
    board = ensure_process_board(node.instance)
    columns = list(board.columns.order_by("position", "id"))
    if not columns:
        return None
    progress = int(node.progress or 0)
    if node.status == ProcessWorkNode.Status.DONE:
        progress = 100
    column = column_for_progress(columns, progress)
    return Card.objects.create(
        column=column,
        process_work_node=node,
        title=node.title[:255],
        description=node.description or "",
        position=node.position,
        due_date=node.end_date,
    )


def sync_card_from_work_node(node: ProcessWorkNode) -> Card | None:
    try:
        card = node.card
    except Card.DoesNotExist:
        card = None
    if card is None:
        if node.node_type == ProcessWorkNode.NodeType.USER_TASK:
            card = ensure_card_for_work_node(node)
        if card is None:
            return None
    columns = list(card.column.board.columns.order_by("position", "id"))
    if not columns:
        return card
    progress = int(node.progress or 0)
    if node.status == ProcessWorkNode.Status.DONE:
        progress = 100
    elif node.status == ProcessWorkNode.Status.CANCELLED:
        progress = 0
    target = column_for_progress(columns, progress)
    fields = ["updated_at"]
    if card.column_id != target.id:
        card.column = target
        fields.append("column")
    if card.title != node.title:
        card.title = node.title[:255]
        fields.append("title")
    if node.end_date and card.due_date != node.end_date:
        card.due_date = node.end_date
        fields.append("due_date")
    card.save(update_fields=fields)
    return card


def sync_work_node_from_card(card: Card) -> None:
    node = card.process_work_node
    if node is None:
        return
    columns = list(card.column.board.columns.order_by("position", "id"))
    if not columns:
        return
    index = next(
        (i for i, col in enumerate(columns) if col.id == card.column_id),
        0,
    )
    if index >= len(columns) - 1 and len(columns) > 1:
        node.status = ProcessWorkNode.Status.DONE
        node.progress = 100
    elif index == 0:
        node.status = ProcessWorkNode.Status.OPEN
        node.progress = 0
    else:
        node.status = ProcessWorkNode.Status.OPEN
        node.progress = round(index / (len(columns) - 1) * 100)
    node.save(update_fields=["status", "progress", "updated_at"])


def ensure_kanban_for_instance(instance: ProcessInstance) -> Board | None:
    """Create board + cards for all UserTask work nodes; return board."""
    nodes = list(
        ProcessWorkNode.objects.filter(
            instance=instance,
            node_type=ProcessWorkNode.NodeType.USER_TASK,
        )
    )
    if not nodes:
        return None
    board = ensure_process_board(instance)
    for node in nodes:
        sync_card_from_work_node(node)
    return board
