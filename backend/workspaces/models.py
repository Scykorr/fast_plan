import hashlib
import secrets

from django.conf import settings
from django.db import models
from django.utils import timezone


class Workspace(models.Model):
    class Currency(models.TextChoices):
        RUB = "RUB", "Russian Ruble"
        USD = "USD", "US Dollar"
        EUR = "EUR", "Euro"

    name = models.CharField(max_length=255)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="owned_workspaces",
    )
    currency = models.CharField(
        max_length=3,
        choices=Currency.choices,
        default=Currency.RUB,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class WorkspaceMember(models.Model):
    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        EDITOR = "editor", "Editor"
        VIEWER = "viewer", "Viewer"

    class CrmRole(models.TextChoices):
        NONE = "", "None"
        SALES_LEAD = "sales_lead", "Sales lead"
        SALES = "sales", "Sales"
        SUPPORT = "support", "Support"

    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="workspace_memberships",
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.OWNER)
    crm_role = models.CharField(
        max_length=20,
        choices=CrmRole.choices,
        blank=True,
        default="",
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("workspace", "user")]

    def __str__(self):
        return f"{self.user} @ {self.workspace}"


class WorkspaceInvitation(models.Model):
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="invitations",
    )
    email = models.EmailField()
    role = models.CharField(
        max_length=20,
        choices=WorkspaceMember.Role.choices,
        default=WorkspaceMember.Role.EDITOR,
    )
    token = models.CharField(max_length=64, unique=True, db_index=True)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_invitations",
    )
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("workspace", "email")]

    def __str__(self):
        return f"{self.email} → {self.workspace}"

    @property
    def is_expired(self):
        from django.utils import timezone

        return timezone.now() > self.expires_at

    @property
    def is_accepted(self):
        return self.accepted_at is not None


class MemberCapacity(models.Model):
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="member_capacities",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="workspace_capacities",
    )
    hours_per_week = models.PositiveSmallIntegerField(default=40)

    class Meta:
        unique_together = [("workspace", "user")]
        verbose_name_plural = "member capacities"

    def __str__(self):
        return f"{self.user} @ {self.workspace}: {self.hours_per_week}h"


class WorkspaceAPIToken(models.Model):
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="api_tokens",
    )
    name = models.CharField(max_length=100)
    prefix = models.CharField(max_length=12, db_index=True)
    token_hash = models.CharField(max_length=64, unique=True)
    scopes = models.JSONField(default=list)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_workspace_tokens",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    @classmethod
    def issue(cls, *, workspace, name, scopes, created_by, expires_at=None):
        raw = f"fp_{secrets.token_urlsafe(32)}"
        token = cls.objects.create(
            workspace=workspace,
            name=name,
            prefix=raw[:12],
            token_hash=hashlib.sha256(raw.encode()).hexdigest(),
            scopes=scopes,
            created_by=created_by,
            expires_at=expires_at,
        )
        return token, raw

    def matches(self, raw_token):
        digest = hashlib.sha256(raw_token.encode()).hexdigest()
        return secrets.compare_digest(self.token_hash, digest)

    @property
    def is_active(self):
        return self.revoked_at is None and (
            self.expires_at is None or self.expires_at > timezone.now()
        )


class WebhookEndpoint(models.Model):
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="webhook_endpoints",
    )
    name = models.CharField(max_length=100)
    url = models.URLField(max_length=500)
    secret = models.CharField(max_length=128)
    events = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_webhooks",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} → {self.url}"


class WebhookDelivery(models.Model):
    endpoint = models.ForeignKey(
        WebhookEndpoint,
        on_delete=models.CASCADE,
        related_name="deliveries",
    )
    event = models.CharField(max_length=100)
    payload = models.JSONField(default=dict)
    dedupe_key = models.CharField(max_length=255, null=True, blank=True, unique=True)
    status_code = models.PositiveSmallIntegerField(null=True, blank=True)
    response_body = models.TextField(blank=True)
    error = models.TextField(blank=True)
    attempt_count = models.PositiveSmallIntegerField(default=0)
    delivered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class ExchangeRate(models.Model):
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="exchange_rates",
    )
    currency = models.CharField(max_length=3, choices=Workspace.Currency.choices)
    rate_to_base = models.DecimalField(
        max_digits=18,
        decimal_places=8,
        help_text="How many base-currency units equal 1 unit of this currency.",
    )
    as_of = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-as_of", "-id"]
        unique_together = [("workspace", "currency", "as_of")]

    def __str__(self):
        return f"{self.currency}@{self.as_of}={self.rate_to_base}"
