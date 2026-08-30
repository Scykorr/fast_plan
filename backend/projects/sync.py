from kanban.models import Card, Column
from projects.models import ScheduleActivity, WBSNode


def progress_for_column(card: Card) -> int:
    columns = list(card.column.board.columns.order_by("position", "id"))
    if not columns:
        return 0

    index = next(
        (i for i, column in enumerate(columns) if column.id == card.column_id),
        0,
    )
    if index == 0:
        return 0
    if index == len(columns) - 1:
        return 100
    return round(index / (len(columns) - 1) * 100)


def column_for_progress(columns: list[Column], progress: int) -> Column:
    if not columns:
        raise ValueError("Board has no columns.")
    if len(columns) == 1:
        return columns[0]
    if progress >= 100:
        return columns[-1]
    if progress > 0:
        return columns[1] if len(columns) > 2 else columns[-1]
    return columns[0]


def sync_card_from_activity(activity: ScheduleActivity) -> None:
    card = getattr(activity.wbs_node, "card", None)
    if card is None:
        return

    columns = list(card.column.board.columns.order_by("position", "id"))
    if not columns:
        return

    target_column = column_for_progress(columns, activity.progress)
    if card.column_id != target_column.id:
        card.column = target_column
        card.save(update_fields=["column", "updated_at"])


def sync_activity_from_card(card: Card) -> None:
    wbs_node = card.wbs_node
    if wbs_node is None:
        return

    schedule = getattr(wbs_node, "schedule", None)
    if schedule is None:
        return

    progress = progress_for_column(card)
    if schedule.progress != progress:
        schedule.progress = progress
        schedule.save(update_fields=["progress"])


def sync_schedule_from_workflow_status(node: WBSNode) -> None:
    """Closed workflow status → 100% schedule progress + Kanban column sync."""
    status = getattr(node, "workflow_status", None)
    if status is None or not status.is_closed:
        return

    schedule = getattr(node, "schedule", None)
    if schedule is None:
        schedule = ScheduleActivity.objects.filter(wbs_node=node).first()
    if schedule is None:
        return

    if schedule.progress != 100:
        schedule.progress = 100
        schedule.save(update_fields=["progress"])
    sync_card_from_activity(schedule)
