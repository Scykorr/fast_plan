from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    email = models.EmailField(unique=True)
    email_verified_at = models.DateTimeField(null=True, blank=True)
    avatar = models.ImageField(upload_to="avatars/%Y/%m/", null=True, blank=True)
    active_workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="active_users",
    )
    totp_secret = models.CharField(max_length=64, blank=True, default="")
    totp_enabled_at = models.DateTimeField(null=True, blank=True)
    # SHA-256 hashes of one-time backup codes
    totp_backup_codes = models.JSONField(default=list, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        return self.email

    @property
    def is_email_verified(self):
        return self.email_verified_at is not None

    @property
    def is_totp_enabled(self):
        return bool(self.totp_secret) and self.totp_enabled_at is not None

    def verify_email(self):
        if self.email_verified_at is None:
            self.email_verified_at = timezone.now()
            self.save(update_fields=["email_verified_at"])


class AuthSession(models.Model):
    """Tracked login session bound to a refresh-token jti (P7 session management)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="auth_sessions",
    )
    refresh_jti = models.CharField(max_length=64, unique=True)
    user_agent = models.CharField(max_length=400, blank=True, default="")
    ip_address = models.CharField(max_length=64, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-last_seen_at", "-id"]

    def __str__(self):
        return f"session {self.refresh_jti[:8]}… for {self.user_id}"


class SocialAccount(models.Model):
    """OAuth identity linked to a User (P7 SSO)."""

    class Provider(models.TextChoices):
        GOOGLE = "google", "Google"
        MICROSOFT = "microsoft", "Microsoft"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="social_accounts",
    )
    provider = models.CharField(max_length=32, choices=Provider.choices)
    uid = models.CharField(max_length=255)
    email = models.EmailField(blank=True, default="")
    extra_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "uid"],
                name="uniq_social_provider_uid",
            )
        ]

    def __str__(self):
        return f"{self.provider}:{self.uid} → {self.user_id}"
