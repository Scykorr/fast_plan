from django.db.models.signals import post_save
from django.dispatch import receiver

from kanban.models import Board, Column
from workspaces.models import Workspace

DEFAULT_COLUMNS = ("К выполнению", "В работе", "Готово")


@receiver(post_save, sender=Workspace)
def create_default_board(sender, instance, created, **kwargs):
    if not created:
        return
    board = Board.objects.create(
        workspace=instance,
        title="Моя доска",
        position=0,
    )
    for index, title in enumerate(DEFAULT_COLUMNS):
        Column.objects.create(board=board, title=title, position=index)
