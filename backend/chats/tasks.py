from celery import shared_task

from chats.services import archive_disabled_rooms


@shared_task(name="chats.archive_disabled_rooms")
def archive_disabled_rooms_task(older_than_days: int = 30) -> int:
    return archive_disabled_rooms(older_than_days=older_than_days)
