from rest_framework import serializers

from chats.gif_allowlist import validate_gif_url
from chats.models import (
    ChatMessage,
    ChatReaction,
    ChatRoom,
    ChatRoomKeyWrap,
    ChatRoomMute,
    ChatUserCryptoKey,
)


class ChatMuteSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    user_id = serializers.IntegerField(source="user.id", read_only=True)

    class Meta:
        model = ChatRoomMute
        fields = ["id", "user_id", "user_email", "reason", "created_at", "muted_by"]
        read_only_fields = fields


class ChatReactionSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="user.id", read_only=True)

    class Meta:
        model = ChatReaction
        fields = ["id", "kind", "emoji", "gif_url", "user_id", "created_at"]
        read_only_fields = fields


class ChatMessageSerializer(serializers.ModelSerializer):
    author_email = serializers.SerializerMethodField()
    author_id = serializers.IntegerField(source="author.id", read_only=True, allow_null=True)
    attachment_url = serializers.SerializerMethodField()
    voice_url = serializers.SerializerMethodField()
    reactions = serializers.SerializerMethodField()
    reply_to_preview = serializers.SerializerMethodField()
    is_deleted = serializers.SerializerMethodField()

    class Meta:
        model = ChatMessage
        fields = [
            "id",
            "room",
            "author_id",
            "author_email",
            "guest_name",
            "body",
            "is_encrypted",
            "reply_to",
            "reply_to_preview",
            "forwarded_from",
            "forward_source_label",
            "attachment_url",
            "voice_url",
            "voice_duration_seconds",
            "reactions",
            "edited_at",
            "deleted_at",
            "is_deleted",
            "created_at",
        ]
        read_only_fields = fields

    def get_author_email(self, obj):
        if obj.author_id:
            return obj.author.email
        return obj.guest_name or "Гость"

    def get_is_deleted(self, obj):
        return obj.is_deleted

    def _file_url(self, field):
        if not field:
            return None
        request = self.context.get("request")
        url = field.url
        if request is not None:
            return request.build_absolute_uri(url)
        return url

    def get_attachment_url(self, obj):
        if obj.is_deleted:
            return None
        return self._file_url(obj.attachment)

    def get_voice_url(self, obj):
        if obj.is_deleted:
            return None
        return self._file_url(obj.voice)

    def get_reactions(self, obj):
        reactions = getattr(obj, "_prefetched_reactions", None)
        if reactions is None:
            reactions = obj.reactions.select_related("user").all()
        counts: dict[str, dict] = {}
        for reaction in reactions:
            key = reaction.reaction_key
            bucket = counts.setdefault(
                key,
                {
                    "kind": reaction.kind,
                    "emoji": reaction.emoji or None,
                    "gif_url": reaction.gif_url or None,
                    "count": 0,
                    "user_ids": [],
                },
            )
            bucket["count"] += 1
            bucket["user_ids"].append(reaction.user_id)
        return list(counts.values())

    def get_reply_to_preview(self, obj):
        parent = obj.reply_to
        if parent is None:
            return None
        if parent.is_deleted:
            return {
                "id": parent.id,
                "body": "[удалено]",
                "author_email": "",
                "is_encrypted": False,
            }
        email = parent.author.email if parent.author_id else (parent.guest_name or "Гость")
        body = "🔒 Зашифровано" if parent.is_encrypted else (parent.body or "")[:120]
        return {
            "id": parent.id,
            "body": body,
            "author_email": email,
            "is_encrypted": parent.is_encrypted,
        }


class ChatRoomSerializer(serializers.ModelSerializer):
    label = serializers.SerializerMethodField()
    project_id = serializers.IntegerField(source="project.id", read_only=True, allow_null=True)
    workspace_id = serializers.SerializerMethodField()
    dm_peer_email = serializers.SerializerMethodField()
    dm_peer_id = serializers.SerializerMethodField()
    can_post = serializers.SerializerMethodField()
    is_moderator = serializers.SerializerMethodField()
    is_muted = serializers.SerializerMethodField()
    is_archived = serializers.SerializerMethodField()
    e2e_enabled = serializers.SerializerMethodField()
    mutes = serializers.SerializerMethodField()

    class Meta:
        model = ChatRoom
        fields = [
            "id",
            "scope",
            "status",
            "label",
            "project_id",
            "workspace_id",
            "dm_peer_email",
            "dm_peer_id",
            "can_post",
            "is_moderator",
            "is_muted",
            "is_archived",
            "e2e_enabled",
            "mutes",
            "status_changed_at",
            "archived_at",
            "created_at",
        ]
        read_only_fields = fields

    def get_label(self, obj):
        return obj.display_label()

    def get_workspace_id(self, obj):
        return obj.host_workspace_id

    def _dm_peer(self, obj):
        request = self.context.get("request")
        if obj.scope != ChatRoom.Scope.DM or request is None:
            return None
        user = request.user
        return obj.dm_user_high if user.id == obj.dm_user_low_id else obj.dm_user_low

    def get_dm_peer_email(self, obj):
        peer = self._dm_peer(obj)
        return peer.email if peer else None

    def get_dm_peer_id(self, obj):
        peer = self._dm_peer(obj)
        return peer.id if peer else None

    def get_e2e_enabled(self, obj):
        return obj.scope == ChatRoom.Scope.DM

    def _meta_flags(self):
        return self.context.get("meta") or {}

    def get_can_post(self, obj):
        return self._meta_flags().get("can_post", False)

    def get_is_moderator(self, obj):
        return self._meta_flags().get("is_moderator", False)

    def get_is_muted(self, obj):
        return self._meta_flags().get("is_muted", False)

    def get_is_archived(self, obj):
        return obj.is_archived

    def get_mutes(self, obj):
        if not self._meta_flags().get("is_moderator"):
            return []
        mutes = obj.mutes.select_related("user", "muted_by").all()
        return ChatMuteSerializer(mutes, many=True).data


class ChatRoomStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=[
            ChatRoom.Status.OPEN,
            ChatRoom.Status.DISABLED,
            ChatRoom.Status.ANNOUNCEMENTS,
            ChatRoom.Status.ARCHIVED,
        ]
    )


class ChatMuteWriteSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    reason = serializers.CharField(required=False, allow_blank=True, max_length=255, default="")


class ChatMessageWriteSerializer(serializers.Serializer):
    body = serializers.CharField(required=False, allow_blank=True, default="")
    is_encrypted = serializers.BooleanField(required=False, default=False)
    reply_to = serializers.IntegerField(required=False, allow_null=True)
    guest_name = serializers.CharField(required=False, allow_blank=True, max_length=120, default="")
    voice_duration_seconds = serializers.IntegerField(required=False, allow_null=True, min_value=1)


class ChatMessageEditSerializer(serializers.Serializer):
    body = serializers.CharField(allow_blank=False, max_length=20000)
    is_encrypted = serializers.BooleanField(required=False, default=False)


class ChatForwardSerializer(serializers.Serializer):
    target_chat_id = serializers.IntegerField()


class ChatReactionWriteSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(
        choices=[ChatReaction.Kind.EMOJI, ChatReaction.Kind.GIF],
        required=False,
        default=ChatReaction.Kind.EMOJI,
    )
    emoji = serializers.CharField(required=False, allow_blank=True, max_length=32, default="")
    gif_url = serializers.URLField(required=False, allow_blank=True, max_length=500, default="")

    def validate(self, attrs):
        kind = attrs.get("kind") or ChatReaction.Kind.EMOJI
        emoji = (attrs.get("emoji") or "").strip()
        gif_url = (attrs.get("gif_url") or "").strip()
        if kind == ChatReaction.Kind.EMOJI:
            if not emoji:
                raise serializers.ValidationError({"emoji": "Required for emoji reactions."})
            if gif_url:
                raise serializers.ValidationError({"gif_url": "Must be empty for emoji."})
            attrs["emoji"] = emoji
            attrs["gif_url"] = ""
        else:
            if not gif_url:
                raise serializers.ValidationError({"gif_url": "Required for GIF reactions."})
            if emoji:
                raise serializers.ValidationError({"emoji": "Must be empty for GIF."})
            try:
                attrs["gif_url"] = validate_gif_url(gif_url)
            except ValueError as exc:
                raise serializers.ValidationError({"gif_url": str(exc)}) from exc
            attrs["emoji"] = ""
        attrs["kind"] = kind
        return attrs


class ChatDmCreateSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()


class ChatCryptoKeySerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="user.id", read_only=True)

    class Meta:
        model = ChatUserCryptoKey
        fields = ["user_id", "public_jwk", "updated_at"]
        read_only_fields = ["user_id", "updated_at"]


class ChatCryptoKeyWriteSerializer(serializers.Serializer):
    public_jwk = serializers.JSONField()

    def validate_public_jwk(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("public_jwk must be an object.")
        if value.get("kty") != "EC" or value.get("crv") != "P-256":
            raise serializers.ValidationError("Only ECDH P-256 public JWK is supported.")
        if not value.get("x") or not value.get("y"):
            raise serializers.ValidationError("public_jwk requires x and y.")
        return {
            "kty": "EC",
            "crv": "P-256",
            "x": value["x"],
            "y": value["y"],
            "ext": True,
            "key_ops": ["deriveBits", "deriveKey"],
        }


class ChatRoomKeyWrapSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="user.id", read_only=True)

    class Meta:
        model = ChatRoomKeyWrap
        fields = ["user_id", "wrapped_key", "updated_at"]
        read_only_fields = fields


class ChatRoomKeyWrapWriteSerializer(serializers.Serializer):
    wraps = serializers.ListField(
        child=serializers.DictField(),
        min_length=1,
        max_length=2,
    )

    def validate_wraps(self, value):
        cleaned = []
        for item in value:
            if not isinstance(item, dict):
                raise serializers.ValidationError("Each wrap must be an object.")
            user_id = item.get("user_id")
            wrapped_key = item.get("wrapped_key")
            if not isinstance(user_id, int):
                raise serializers.ValidationError("user_id must be an integer.")
            if not isinstance(wrapped_key, str) or not wrapped_key.strip():
                raise serializers.ValidationError("wrapped_key is required.")
            if len(wrapped_key) > 8000:
                raise serializers.ValidationError("wrapped_key is too large.")
            cleaned.append({"user_id": user_id, "wrapped_key": wrapped_key.strip()})
        return cleaned


class ChatRoomListItemSerializer(serializers.ModelSerializer):
    label = serializers.SerializerMethodField()
    project_id = serializers.IntegerField(source="project.id", read_only=True, allow_null=True)
    workspace_id = serializers.SerializerMethodField()
    dm_peer_email = serializers.SerializerMethodField()

    class Meta:
        model = ChatRoom
        fields = [
            "id",
            "scope",
            "status",
            "label",
            "project_id",
            "workspace_id",
            "dm_peer_email",
            "archived_at",
        ]

    def get_label(self, obj):
        return obj.display_label()

    def get_workspace_id(self, obj):
        return obj.host_workspace_id

    def get_dm_peer_email(self, obj):
        request = self.context.get("request")
        if obj.scope != ChatRoom.Scope.DM or request is None:
            return None
        user = request.user
        peer = obj.dm_user_high if user.id == obj.dm_user_low_id else obj.dm_user_low
        return peer.email if peer else None
