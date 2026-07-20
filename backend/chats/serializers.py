from rest_framework import serializers

from chats.models import ChatMessage, ChatReaction, ChatRoom, ChatRoomMute


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
        fields = ["id", "emoji", "user_id", "created_at"]
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
            bucket = counts.setdefault(
                reaction.emoji,
                {"emoji": reaction.emoji, "count": 0, "user_ids": []},
            )
            bucket["count"] += 1
            bucket["user_ids"].append(reaction.user_id)
        return list(counts.values())

    def get_reply_to_preview(self, obj):
        parent = obj.reply_to
        if parent is None:
            return None
        if parent.is_deleted:
            return {"id": parent.id, "body": "[удалено]", "author_email": ""}
        email = parent.author.email if parent.author_id else (parent.guest_name or "Гость")
        return {
            "id": parent.id,
            "body": (parent.body or "")[:120],
            "author_email": email,
        }


class ChatRoomSerializer(serializers.ModelSerializer):
    label = serializers.SerializerMethodField()
    project_id = serializers.IntegerField(source="project.id", read_only=True, allow_null=True)
    workspace_id = serializers.SerializerMethodField()
    dm_peer_email = serializers.SerializerMethodField()
    can_post = serializers.SerializerMethodField()
    is_moderator = serializers.SerializerMethodField()
    is_muted = serializers.SerializerMethodField()
    is_archived = serializers.SerializerMethodField()
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
            "can_post",
            "is_moderator",
            "is_muted",
            "is_archived",
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

    def get_dm_peer_email(self, obj):
        request = self.context.get("request")
        if obj.scope != ChatRoom.Scope.DM or request is None:
            return None
        user = request.user
        peer = obj.dm_user_high if user.id == obj.dm_user_low_id else obj.dm_user_low
        return peer.email if peer else None

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
    reply_to = serializers.IntegerField(required=False, allow_null=True)
    guest_name = serializers.CharField(required=False, allow_blank=True, max_length=120, default="")
    voice_duration_seconds = serializers.IntegerField(required=False, allow_null=True, min_value=1)


class ChatMessageEditSerializer(serializers.Serializer):
    body = serializers.CharField(allow_blank=False, max_length=10000)


class ChatForwardSerializer(serializers.Serializer):
    target_chat_id = serializers.IntegerField()


class ChatReactionWriteSerializer(serializers.Serializer):
    emoji = serializers.CharField(max_length=32)


class ChatDmCreateSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()


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
