from django.conf import settings
from django.db import models


class TimeEntry(models.Model):
    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="time_entries",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="time_entries",
    )
    wbs_node = models.ForeignKey(
        "projects.WBSNode",
        on_delete=models.CASCADE,
        related_name="time_entries",
    )
    hours = models.DecimalField(max_digits=6, decimal_places=2)
    work_date = models.DateField()
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-work_date", "-id"]

    def __str__(self):
        return f"{self.user} — {self.wbs_node} — {self.hours}h ({self.work_date})"
