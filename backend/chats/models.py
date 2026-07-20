from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class ChatRoom(models.Model):
    class Scope(models.TextChoices):
        PROJECT = "project", "Project"
        WORKSPACE = "workspace", "Workspace"
        DM = "dm", "Direct message"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        DISABLED = "disabled", "Disabled"
        ANNOUNCEMENTS = "announcements", "Announcements only"
        ARCHIVED = "archived", "Archived"

    scope = models.CharField(max_length=20, choices=Scope.choices)
    project = models.OneToOneField(
        "projects.Project",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="chat_room",
    )
    # Portfolio chat: one room per workspace (enforced by UniqueConstraint).
    # DM rooms also point at host workspace (many DMs per workspace).
    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="chat_rooms",
    )
    dm_user_low = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="dm_rooms_as_low",
    )
    dm_user_high = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="dm_rooms_as_high",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
    )
    status_changed_at = models.DateTimeField(null=True, blank=True)
    status_changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="chat_status_changes",
    )
    archived_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(
                        scope="project",
                        project__isnull=False,
                        workspace__isnull=True,
                        dm_user_low__isnull=True,
                        dm_user_high__isnull=True,
                    )
                    | Q(
                        scope="workspace",
                        project__isnull=True,
                        workspace__isnull=False,
                        dm_user_low__isnull=True,
                        dm_user_high__isnull=True,
                    )
                    | Q(
                        scope="dm",
                        project__isnull=True,
                        workspace__isnull=False,
                        dm_user_low__isnull=False,
                        dm_user_high__isnull=False,
                    )
                ),
                name="chatroom_scope_target_xor",
            ),
            models.UniqueConstraint(
                fields=["workspace"],
                condition=Q(scope="workspace"),
                name="uniq_chatroom_workspace_scope",
            ),
            models.UniqueConstraint(
                fields=["workspace", "dm_user_low", "dm_user_high"],
                condition=Q(scope="dm"),
                name="uniq_chatroom_dm_pair",
            ),
        ]

    def __str__(self):
        if self.scope == self.Scope.PROJECT and self.project_id:
            return f"Chat project:{self.project_id}"
        if self.scope == self.Scope.DM:
            return f"Chat dm:{self.dm_user_low_id}-{self.dm_user_high_id}"
        return f"Chat workspace:{self.workspace_id}"

    def clean(self):
        if self.scope == self.Scope.PROJECT:
            if self.project_id is None or self.workspace_id is not None:
                raise ValidationError("Project chat requires project FK only.")
        elif self.scope == self.Scope.WORKSPACE:
            if self.workspace_id is None or self.project_id is not None:
                raise ValidationError("Workspace chat requires workspace FK only.")
        elif self.scope == self.Scope.DM:
            if (
                self.workspace_id is None
                or self.dm_user_low_id is None
                or self.dm_user_high_id is None
                or self.dm_user_low_id >= self.dm_user_high_id
            ):
                raise ValidationError("DM requires workspace and ordered user pair.")

    @property
    def host_workspace_id(self) -> int:
        if self.scope == self.Scope.PROJECT:
            return self.project.workspace_id
        return self.workspace_id

    @property
    def is_archived(self) -> bool:
        return self.status == self.Status.ARCHIVED or self.archived_at is not None

    def display_label(self) -> str:
        if self.scope == self.Scope.PROJECT and self.project_id:
            return f"Проект «{self.project.name}»"
        if self.scope == self.Scope.DM:
            low = getattr(self.dm_user_low, "email", self.dm_user_low_id)
            high = getattr(self.dm_user_high, "email", self.dm_user_high_id)
            return f"DM: {low} ↔ {high}"
        if self.workspace_id:
            return f"Портфель «{self.workspace.name}»"
        return "Чат"


class ChatRoomMute(models.Model):
    room = models.ForeignKey(
        ChatRoom,
        on_delete=models.CASCADE,
        related_name="mutes",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_mutes",
    )
    muted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="chat_mutes_created",
    )
    reason = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(fields=["room", "user"], name="uniq_chatroom_mute_user"),
        ]

    def __str__(self):
        return f"Mute {self.user_id} in room {self.room_id}"


class ChatMessage(models.Model):
    room = models.ForeignKey(
        ChatRoom,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="chat_messages",
    )
    guest_name = models.CharField(max_length=120, blank=True, default="")
    body = models.TextField(blank=True, default="")
    is_encrypted = models.BooleanField(default=False)
    reply_to = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="replies",
    )
    forwarded_from = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="forwards",
    )
    forward_source_label = models.CharField(max_length=255, blank=True, default="")
    attachment = models.FileField(upload_to="chat_attachments/%Y/%m/", blank=True)
    voice = models.FileField(upload_to="chat_voice/%Y/%m/", blank=True)
    voice_duration_seconds = models.PositiveIntegerField(null=True, blank=True)
    edited_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="chat_messages_deleted",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"Message {self.id} in room {self.room_id}"

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None


class ChatReaction(models.Model):
    class Kind(models.TextChoices):
        EMOJI = "emoji", "Emoji"
        GIF = "gif", "GIF"

    message = models.ForeignKey(
        ChatMessage,
        on_delete=models.CASCADE,
        related_name="reactions",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_reactions",
    )
    kind = models.CharField(
        max_length=10,
        choices=Kind.choices,
        default=Kind.EMOJI,
    )
    emoji = models.CharField(max_length=32, blank=True, default="")
    gif_url = models.URLField(max_length=500, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["message", "user", "kind", "emoji", "gif_url"],
                name="uniq_chat_reaction_user_token",
            ),
            models.CheckConstraint(
                condition=(
                    Q(kind="emoji", emoji__gt="", gif_url="")
                    | Q(kind="gif", gif_url__gt="", emoji="")
                ),
                name="chat_reaction_kind_payload",
            ),
        ]

    def __str__(self):
        token = self.emoji or self.gif_url
        return f"{self.kind}:{token} on message {self.message_id}"

    @property
    def reaction_key(self) -> str:
        if self.kind == self.Kind.GIF:
            return f"gif:{self.gif_url}"
        return f"emoji:{self.emoji}"


class ChatUserCryptoKey(models.Model):
    """Published ECDH P-256 public key for DM E2E (private key stays on client)."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_crypto_key",
    )
    public_jwk = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Crypto key for user {self.user_id}"


class ChatRoomKeyWrap(models.Model):
    """AES room key wrapped for a DM participant (ciphertext opaque to server)."""

    room = models.ForeignKey(
        ChatRoom,
        on_delete=models.CASCADE,
        related_name="key_wraps",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_key_wraps",
    )
    wrapped_key = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["room", "user"],
                name="uniq_chat_room_key_wrap_user",
            ),
        ]

    def __str__(self):
        return f"Key wrap room={self.room_id} user={self.user_id}"
