from datetime import datetime, time, timedelta

from django.utils import timezone

from kanban.models import Card


def build_board_flow_analytics(board, *, days=14):
    days = max(7, min(int(days), 90))
    today = timezone.localdate()
    start = today - timedelta(days=days - 1)
    columns = list(board.columns.order_by("position", "id"))
    if not columns:
        return {"board_id": board.id, "burndown": [], "velocity": []}
    done_column = columns[-1]
    cards = list(
        Card.objects.filter(column__board=board).prefetch_related("transitions")
    )

    burndown = []
    for offset in range(days):
        day = start + timedelta(days=offset)
        end_of_day = timezone.make_aware(datetime.combine(day, time.max))
        remaining = 0
        for card in cards:
            if card.created_at > end_of_day:
                continue
            column_id = card.column_id
            transitions = sorted(
                card.transitions.all(),
                key=lambda item: item.occurred_at,
                reverse=True,
            )
            for transition in transitions:
                if transition.occurred_at > end_of_day:
                    column_id = transition.from_column_id
            if column_id != done_column.id:
                remaining += 1
        burndown.append({"date": day.isoformat(), "remaining": remaining})

    initial = burndown[0]["remaining"] if burndown else 0
    denominator = max(days - 1, 1)
    for index, point in enumerate(burndown):
        point["ideal"] = round(initial * (1 - index / denominator), 1)

    velocity = []
    week_start = today - timedelta(days=today.weekday(), weeks=3)
    transitions = [
        transition
        for card in cards
        for transition in card.transitions.all()
        if transition.to_column_id == done_column.id
    ]
    for week_offset in range(4):
        current_start = week_start + timedelta(weeks=week_offset)
        current_end = current_start + timedelta(days=7)
        completed_ids = {
            transition.card_id
            for transition in transitions
            if current_start <= timezone.localdate(transition.occurred_at) < current_end
        }
        velocity.append(
            {
                "week_start": current_start.isoformat(),
                "completed": len(completed_ids),
            }
        )
    return {
        "board_id": board.id,
        "done_column_id": done_column.id,
        "burndown": burndown,
        "velocity": velocity,
    }
