from django.conf import settings
from django.db import models


def attachment_upload_path(instance, filename):
    if instance.wbs_node_id:
        return f"attachments/wbs/{instance.wbs_node_id}/{filename}"
    return f"attachments/cards/{instance.card_id}/{filename}"


class WorkItemAttachment(models.Model):
    wbs_node = models.ForeignKey(
        "projects.WBSNode",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="attachments",
    )
    card = models.ForeignKey(
        "kanban.Card",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="attachments",
    )
    file = models.FileField(upload_to=attachment_upload_path)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_attachments",
    )
    name = models.CharField(max_length=255)
    size = models.PositiveBigIntegerField(default=0)
    content_type = models.CharField(max_length=150, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(wbs_node__isnull=False, card__isnull=True)
                    | models.Q(wbs_node__isnull=True, card__isnull=False)
                ),
                name="workitemattachment_exactly_one_target",
            )
        ]

    def __str__(self):
        return self.name
