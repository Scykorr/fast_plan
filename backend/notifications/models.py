from django.db import models
from django.db.models import Q

from django.conf import settings


class Notification(models.Model):
    class NotificationType(models.TextChoices):
        BIRTHDAY = "birthday", "Birthday"
        MILESTONE = "milestone", "Milestone"
        RISK = "risk", "Risk"
        DEADLINE = "deadline", "Deadline"
        INVITE = "invite", "Invite"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
    )
    notification_type = models.CharField(
        max_length=20,
        choices=NotificationType.choices,
    )
    title = models.CharField(max_length=255)
    message = models.TextField(blank=True)
    link = models.CharField(max_length=500, blank=True)
    dedupe_key = models.CharField(max_length=255, blank=True, default="")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "dedupe_key"],
                condition=~Q(dedupe_key=""),
                name="uniq_notification_user_dedupe_key",
            )
        ]

    def __str__(self):
        return self.title
