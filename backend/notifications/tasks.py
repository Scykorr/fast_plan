import logging

from celery import shared_task

from notifications.services import run_all_reminders

logger = logging.getLogger("fast_plan")


@shared_task(name="notifications.run_reminders")
def run_reminders() -> dict[str, int]:
    """Celery task wrapper around ``run_all_reminders`` (birthdays/milestones/deadlines)."""
    stats = run_all_reminders()
    logger.info("run_reminders task finished: %s", stats)
    return stats
