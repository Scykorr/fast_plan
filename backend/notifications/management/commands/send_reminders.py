from django.core.cache import cache
from django.core.management.base import BaseCommand

from notifications.services import run_all_reminders

# Cross-process lock via the Django cache. When REDIS_URL is configured the
# cache backend is shared across processes/containers, so this protects
# concurrent runs (e.g. the shell scheduler loop and a Celery beat task
# firing at the same time). Without Redis the cache falls back to per-process
# LocMemCache, so the lock only protects against concurrent runs *within the
# same process* — avoid running multiple scheduler processes without Redis.
LOCK_KEY = "send_reminders:lock"
LOCK_TIMEOUT_SECONDS = 60 * 10


class Command(BaseCommand):
    help = "Create birthday, milestone and deadline reminder notifications (idempotent)."

    def handle(self, *args, **options):
        if not cache.add(LOCK_KEY, "locked", timeout=LOCK_TIMEOUT_SECONDS):
            self.stdout.write(
                self.style.WARNING(
                    "send_reminders: lock already held elsewhere — skipping this run."
                )
            )
            return
        try:
            stats = run_all_reminders()
        finally:
            cache.delete(LOCK_KEY)
        self.stdout.write(
            self.style.SUCCESS(
                "Reminders: "
                f"birthdays={stats['birthdays']} "
                f"milestones={stats['milestones']} "
                f"deadlines={stats['deadlines']} "
                f"emails={stats.get('emails', 0)} "
                f"(workspaces={stats['workspaces']})"
            )
        )
