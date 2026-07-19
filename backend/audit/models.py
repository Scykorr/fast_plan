from django.conf import settings
from django.db import models


class AuditLogEntry(models.Model):
    """Immutable record of a notable mutation inside a workspace.

    Entries are created via ``audit.services.log_audit`` and are never
    updated or deleted through the API (no PATCH/DELETE endpoints exist).
    """

    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="audit_entries",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_entries",
    )
    action = models.CharField(max_length=100)
    entity_type = models.CharField(max_length=100)
    entity_id = models.PositiveIntegerField(null=True, blank=True)
    summary = models.CharField(max_length=500, blank=True)
    changes = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.action} {self.entity_type}#{self.entity_id}"
