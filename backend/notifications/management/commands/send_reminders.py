from django.core.management.base import BaseCommand

from notifications.services import run_all_reminders


class Command(BaseCommand):
    help = "Create birthday, milestone and deadline reminder notifications (idempotent)."

    def handle(self, *args, **options):
        stats = run_all_reminders()
        self.stdout.write(
            self.style.SUCCESS(
                "Reminders: "
                f"birthdays={stats['birthdays']} "
                f"milestones={stats['milestones']} "
                f"deadlines={stats['deadlines']} "
                f"(workspaces={stats['workspaces']})"
            )
        )
