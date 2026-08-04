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
        null=True,
        blank=True,
        related_name="time_entries",
    )
    process_work_node = models.ForeignKey(
        "process.ProcessWorkNode",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="time_entries",
    )
    hours = models.DecimalField(max_digits=6, decimal_places=2)
    work_date = models.DateField()
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-work_date", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(wbs_node__isnull=False, process_work_node__isnull=True)
                    | models.Q(wbs_node__isnull=True, process_work_node__isnull=False)
                ),
                name="timeentry_exactly_one_target",
            )
        ]

    def __str__(self):
        target = self.wbs_node_id or self.process_work_node_id
        return f"{self.user} — {target} — {self.hours}h ({self.work_date})"
