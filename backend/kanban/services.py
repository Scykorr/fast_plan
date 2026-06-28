from kanban.models import Card, Column


def reorder_positions(cards_queryset):
    for index, card in enumerate(cards_queryset.order_by("position", "id")):
        if card.position != index:
            Card.objects.filter(pk=card.pk).update(position=index)


def move_card(card, target_column: Column, position: int) -> Card:
    source_column = card.column
    target_cards = list(
        target_column.cards.exclude(pk=card.pk).order_by("position", "id")
    )
    position = min(position, len(target_cards))
    target_cards.insert(position, card)

    card.column = target_column
    card.save(update_fields=["column", "updated_at"])

    for index, item in enumerate(target_cards):
        if item.position != index:
            Card.objects.filter(pk=item.pk).update(position=index)

    if source_column.pk != target_column.pk:
        reorder_positions(source_column.cards.all())

    card.refresh_from_db()
    return card
