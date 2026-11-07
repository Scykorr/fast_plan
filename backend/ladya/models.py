"""Ladya Hub: laboratories, work packages, intake (M0 skeleton)."""

from __future__ import annotations

from django.conf import settings
from django.db import models


class LadyaSettings(models.Model):
    """Per-workspace feature flag for Ladya Hub UI/API."""

    workspace = models.OneToOneField(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="ladya_settings",
    )
    ladya_hub_enabled = models.BooleanField(default=False)
    # Shared secret for POST /api/ladya/telegram/<secret>/ (Intake only; never agents).
    telegram_webhook_secret = models.CharField(max_length=64, blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"ladya settings ws={self.workspace_id}"


class Laboratory(models.Model):
    class Kind(models.TextChoices):
        CENTRAL_LAD = "central_lad", "Центральный ЛАД"
        LAB0 = "lab0", "Lab-0 / методологическая"
        PRIVATE_LAB = "private_lab", "Частная лаборатория"
        EXTERNAL_INTAKE = "external_intake", "Вход / очередь людей"

    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="laboratories",
    )
    slug = models.SlugField(max_length=64)
    title = models.CharField(max_length=255)
    kind = models.CharField(max_length=32, choices=Kind.choices)
    is_active = models.BooleanField(default=True)
    # Optional link to an existing workspace/project chat (not a new messenger).
    chat_room = models.ForeignKey(
        "chats.ChatRoom",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ladya_laboratories",
    )
    # Agent Ops profiles bound to this lab (connect wizard).
    agents = models.ManyToManyField(
        "delivery.AgentProfile",
        blank=True,
        related_name="ladya_laboratories",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title"]
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "slug"],
                name="ladya_laboratory_workspace_slug_uniq",
            ),
        ]

    def __str__(self):
        return f"{self.title} ({self.slug})"


class Package(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Черновик"
        SUBMITTED = "submitted", "Отправлен"
        ACCEPTED = "accepted", "Принят"
        IN_PROGRESS = "in_progress", "В работе"
        RETURNED = "returned", "Возвращён"
        CLOSED = "closed", "Закрыт"
        REJECTED = "rejected", "Отклонён"

    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="ladya_packages",
    )
    public_number = models.PositiveIntegerField(editable=False)
    title = models.CharField(max_length=255)
    summary = models.TextField(blank=True, default="")
    from_laboratory = models.ForeignKey(
        Laboratory,
        on_delete=models.PROTECT,
        related_name="packages_sent",
        null=True,
        blank=True,
    )
    to_laboratory = models.ForeignKey(
        Laboratory,
        on_delete=models.PROTECT,
        related_name="packages_received",
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="ladya_packages_created",
    )
    linked_delivery_task = models.ForeignKey(
        "delivery.DeliveryTask",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ladya_packages",
    )
    # Hint for next Agent Ops / Ladya role — not a lifecycle enforcer.
    preferred_role = models.CharField(max_length=32, blank=True, default="")
    manifest_sha256 = models.CharField(max_length=64, blank=True, default="")
    notes_limitations = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "public_number"],
                name="ladya_package_workspace_number_uniq",
            ),
        ]

    def __str__(self):
        return f"PKG-{self.public_number}: {self.title}"

    @property
    def display_code(self) -> str:
        return f"PKG-{self.public_number}"


class PackageStatusEvent(models.Model):
    """Simple audit of package status / recipient changes."""

    package = models.ForeignKey(
        Package,
        on_delete=models.CASCADE,
        related_name="status_events",
    )
    from_status = models.CharField(max_length=32, blank=True, default="")
    to_status = models.CharField(max_length=32)
    from_laboratory = models.ForeignKey(
        Laboratory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    to_laboratory = models.ForeignKey(
        Laboratory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    reason = models.TextField(blank=True, default="")
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ladya_package_status_events",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class PackageFile(models.Model):
    package = models.ForeignKey(
        Package,
        on_delete=models.CASCADE,
        related_name="files",
    )
    file = models.FileField(upload_to="ladya/packages/%Y/%m/")
    original_name = models.CharField(max_length=255)
    size = models.PositiveBigIntegerField(default=0)
    sha256 = models.CharField(max_length=64)
    content_type = models.CharField(max_length=128, blank=True, default="")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ladya_package_files",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.original_name


class IntakeRequest(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "Новая"
        TRIAGED = "triaged", "Разобрана"
        CONVERTED = "converted", "Преобразована в пакет"
        CLOSED = "closed", "Закрыта"

    class Source(models.TextChoices):
        WEB_FORM = "web_form", "Веб-форма"
        MANUAL = "manual", "Вручную"
        INTERNAL_CHAT = "internal_chat", "Внутренний чат Fast Plan"
        # Legacy / unused for Ladya (Telegram out of scope). Kept for DB rows only.
        TELEGRAM = "telegram", "Telegram (deprecated)"

    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="ladya_intake_requests",
    )
    body = models.TextField()
    contact = models.CharField(max_length=255, blank=True, default="")
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.NEW,
    )
    source = models.CharField(
        max_length=32,
        choices=Source.choices,
        default=Source.WEB_FORM,
    )
    package = models.ForeignKey(
        Package,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="intake_requests",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ladya_intake_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Intake #{self.pk} ({self.status})"
