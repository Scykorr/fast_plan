from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from chats.models import (
    ChatMessage,
    ChatReaction,
    ChatRoom,
    ChatRoomKeyWrap,
    ChatRoomMute,
    ChatUserCryptoKey,
)
from chats.serializers import (
    ChatCryptoKeySerializer,
    ChatCryptoKeyWriteSerializer,
    ChatDmCreateSerializer,
    ChatForwardSerializer,
    ChatMessageEditSerializer,
    ChatMessageSerializer,
    ChatMessageWriteSerializer,
    ChatMuteSerializer,
    ChatMuteWriteSerializer,
    ChatReactionWriteSerializer,
    ChatRoomKeyWrapSerializer,
    ChatRoomKeyWrapWriteSerializer,
    ChatRoomListItemSerializer,
    ChatRoomSerializer,
    ChatRoomStatusSerializer,
)
from chats.services import (
    can_access,
    can_delete_message,
    can_edit_message,
    can_forward_into,
    can_post,
    get_or_create_dm_room,
    get_or_create_project_room,
    get_or_create_workspace_room,
    is_moderator,
    is_muted,
    list_accessible_rooms,
)
from notifications.models import Notification
from notifications.services import create_notification, project_deep_link
from projects.models import Project, ProjectShareLink
from workspaces.events import publish_event
from workspaces.mixins import IsWorkspaceMember, WorkspaceMixin
from workspaces.services import get_membership

User = get_user_model()


def _room_meta(room, user):
    return {
        "can_post": can_post(room, user),
        "is_moderator": is_moderator(room, user),
        "is_muted": is_muted(room, user),
    }


def _serialize_room(room, user, request=None):
    return ChatRoomSerializer(
        room,
        context={"request": request, "meta": _room_meta(room, user)},
    ).data


def _validate_upload(upload, *, kind: str = "attachment"):
    if upload is None:
        return
    max_bytes = settings.ATTACHMENT_MAX_BYTES
    if upload.size > max_bytes:
        raise ValidationError({kind: f"File exceeds the {max_bytes} bytes limit."})


def _message_queryset(room):
    return (
        room.messages.select_related("author", "reply_to", "reply_to__author")
        .prefetch_related(
            Prefetch("reactions", queryset=ChatReaction.objects.select_related("user"))
        )
        .order_by("created_at", "id")
    )


def _notify_new_message(message: ChatMessage):
    from chats.services import recipient_users

    room = message.room
    if room.status in {ChatRoom.Status.DISABLED, ChatRoom.Status.ARCHIVED}:
        return

    label = room.display_label()
    if message.is_encrypted:
        preview = "🔒 Зашифрованное сообщение"
    else:
        preview = (message.body or "").strip()[:120] or (
            "Голосовое" if message.voice else ("Вложение" if message.attachment else "Сообщение")
        )
    if room.scope == ChatRoom.Scope.PROJECT:
        link = project_deep_link(room.project, tab="chat")
        workspace = room.project.workspace
    elif room.scope == ChatRoom.Scope.DM:
        link = f"/portfolio?workspace={room.workspace_id}&chat=1&dm={room.id}"
        workspace = room.workspace
    else:
        link = f"/portfolio?workspace={room.workspace_id}&chat=1"
        workspace = room.workspace

    author_id = message.author_id
    for user in recipient_users(room):
        if author_id and user.id == author_id:
            continue
        create_notification(
            user=user,
            notification_type=Notification.NotificationType.CHAT,
            title=f"Чат: {label}",
            message=preview,
            link=link,
            workspace=workspace,
            dedupe_key=f"chat:{message.id}:user:{user.id}",
        )


def _publish_message(message: ChatMessage, event_type: str = "chat.message"):
    room = message.room
    publish_event(
        room.host_workspace_id,
        event_type,
        {
            "room_id": room.id,
            "message_id": message.id,
            "scope": room.scope,
            "project_id": room.project_id,
            "workspace_id": room.host_workspace_id,
        },
    )


def _get_room_for_workspace(room_id, workspace, user):
    room = get_object_or_404(
        ChatRoom.objects.select_related(
            "project",
            "workspace",
            "project__workspace",
            "dm_user_low",
            "dm_user_high",
        ),
        pk=room_id,
    )
    if room.host_workspace_id != workspace.id:
        raise NotFound()
    if not can_access(room, user):
        raise PermissionDenied("No access to this chat.")
    return room


class ChatResolveView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceMember]

    def get(self, request):
        scope = request.query_params.get("scope", "").strip()
        if scope == ChatRoom.Scope.PROJECT:
            project_id = request.query_params.get("project_id")
            if not project_id:
                raise ValidationError({"project_id": "Required for project scope."})
            project = get_object_or_404(
                Project.objects.filter(workspace=self.get_workspace()),
                pk=project_id,
            )
            room = get_or_create_project_room(project)
        elif scope == ChatRoom.Scope.WORKSPACE:
            room = get_or_create_workspace_room(self.get_workspace())
        elif scope == ChatRoom.Scope.DM:
            raise ValidationError({"scope": "Use POST /api/chats/dm/ to open a DM."})
        else:
            raise ValidationError({"scope": "Must be 'project' or 'workspace'."})

        if not can_access(room, request.user):
            raise PermissionDenied("No access to this chat.")
        return Response(_serialize_room(room, request.user, request))


class ChatDmCreateView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceMember]

    def post(self, request):
        serializer = ChatDmCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        workspace = self.get_workspace()
        peer = get_object_or_404(User, pk=serializer.validated_data["user_id"])
        if peer.id == request.user.id:
            raise ValidationError({"user_id": "Cannot start a DM with yourself."})
        if get_membership(workspace, peer) is None:
            raise ValidationError({"user_id": "User is not a workspace member."})
        room = get_or_create_dm_room(workspace, request.user, peer)
        return Response(
            _serialize_room(room, request.user, request),
            status=status.HTTP_201_CREATED,
        )


class ChatMineView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceMember]

    def get(self, request):
        include_archived = request.query_params.get("include_archived") == "1"
        rooms = list_accessible_rooms(request.user, include_archived=include_archived)
        return Response(
            ChatRoomListItemSerializer(
                rooms, many=True, context={"request": request}
            ).data
        )


class ChatDetailView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceMember]

    def get_room(self, room_id):
        return _get_room_for_workspace(room_id, self.get_workspace(), self.request.user)

    def get(self, request, room_id):
        room = self.get_room(room_id)
        return Response(_serialize_room(room, request.user, request))

    def patch(self, request, room_id):
        room = self.get_room(room_id)
        if room.scope == ChatRoom.Scope.DM:
            raise PermissionDenied("DM rooms do not support status moderation.")
        if not is_moderator(room, request.user):
            raise PermissionDenied("Only moderators can change chat status.")
        serializer = ChatRoomStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_status = serializer.validated_data["status"]
        if room.status != new_status:
            room.status = new_status
            room.status_changed_at = timezone.now()
            room.status_changed_by = request.user
            updates = ["status", "status_changed_at", "status_changed_by"]
            if new_status == ChatRoom.Status.ARCHIVED:
                room.archived_at = timezone.now()
                updates.append("archived_at")
            elif room.archived_at and new_status != ChatRoom.Status.ARCHIVED:
                room.archived_at = None
                updates.append("archived_at")
            room.save(update_fields=updates)
        return Response(_serialize_room(room, request.user, request))


class ChatMuteListCreateView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceMember]

    def get_room(self, room_id):
        return _get_room_for_workspace(room_id, self.get_workspace(), self.request.user)

    def get(self, request, room_id):
        room = self.get_room(room_id)
        if not is_moderator(room, request.user):
            raise PermissionDenied("Only moderators can view mutes.")
        mutes = room.mutes.select_related("user", "muted_by").all()
        return Response(ChatMuteSerializer(mutes, many=True).data)

    def post(self, request, room_id):
        room = self.get_room(room_id)
        if not is_moderator(room, request.user):
            raise PermissionDenied("Only moderators can mute users.")
        serializer = ChatMuteWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target = get_object_or_404(User, pk=serializer.validated_data["user_id"])
        if not can_access(room, target):
            raise ValidationError({"user_id": "User is not a chat participant."})
        if is_moderator(room, target) and room.scope != ChatRoom.Scope.DM:
            raise ValidationError({"user_id": "Cannot mute a moderator."})
        mute, _ = ChatRoomMute.objects.update_or_create(
            room=room,
            user=target,
            defaults={
                "muted_by": request.user,
                "reason": serializer.validated_data.get("reason", ""),
            },
        )
        return Response(ChatMuteSerializer(mute).data, status=status.HTTP_201_CREATED)


class ChatMuteDetailView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceMember]

    def delete(self, request, room_id, user_id):
        room = _get_room_for_workspace(room_id, self.get_workspace(), request.user)
        if not is_moderator(room, request.user):
            raise PermissionDenied("Only moderators can unmute users.")
        deleted, _ = ChatRoomMute.objects.filter(room=room, user_id=user_id).delete()
        if not deleted:
            raise NotFound()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ChatMessageListCreateView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceMember]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_room(self, room_id):
        return _get_room_for_workspace(room_id, self.get_workspace(), self.request.user)

    def get(self, request, room_id):
        room = self.get_room(room_id)
        if (
            room.status == ChatRoom.Status.DISABLED
            and not is_moderator(room, request.user)
        ):
            return Response(
                {
                    "detail": "Chat is disabled by the moderator.",
                    "status": room.status,
                    "results": [],
                }
            )
        qs = _message_queryset(room)
        parent = request.query_params.get("reply_to")
        if parent:
            qs = qs.filter(reply_to_id=int(parent))
        else:
            # Top-level feed: include all messages (replies inline via reply_to)
            pass
        before = request.query_params.get("before")
        if before:
            qs = qs.filter(id__lt=int(before))
        limit = min(int(request.query_params.get("limit", 50)), 100)
        messages = list(qs[:limit])
        for message in messages:
            message._prefetched_reactions = list(message.reactions.all())
        return Response(
            {
                "results": ChatMessageSerializer(
                    messages, many=True, context={"request": request}
                ).data,
                "status": room.status,
            }
        )

    def post(self, request, room_id):
        room = self.get_room(room_id)
        if not can_post(room, request.user):
            if room.is_archived:
                raise PermissionDenied("Chat is archived.")
            if room.status == ChatRoom.Status.DISABLED:
                raise PermissionDenied("Chat is disabled.")
            if room.status == ChatRoom.Status.ANNOUNCEMENTS:
                raise PermissionDenied("Only moderators can post announcements.")
            if is_muted(room, request.user):
                raise PermissionDenied("You are muted in this chat.")
            raise PermissionDenied("Cannot post to this chat.")

        serializer = ChatMessageWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        body = (serializer.validated_data.get("body") or "").strip()
        is_encrypted = bool(serializer.validated_data.get("is_encrypted"))
        upload = request.FILES.get("attachment")
        voice = request.FILES.get("voice")
        _validate_upload(upload, kind="attachment")
        _validate_upload(voice, kind="voice")
        if is_encrypted:
            if room.scope != ChatRoom.Scope.DM:
                raise ValidationError(
                    {"is_encrypted": "E2E encryption is only supported for DMs."}
                )
            if upload or voice:
                raise ValidationError(
                    {"is_encrypted": "Encrypted messages cannot include attachments yet."}
                )
            if not body:
                raise ValidationError({"body": "Encrypted ciphertext is required."})
        reply_to_id = serializer.validated_data.get("reply_to")
        reply_to = None
        if reply_to_id:
            reply_to = get_object_or_404(room.messages, pk=reply_to_id)
        if not body and not upload and not voice:
            raise ValidationError(
                {"body": "Message body, attachment, or voice is required."}
            )

        message = ChatMessage.objects.create(
            room=room,
            author=request.user,
            body=body,
            is_encrypted=is_encrypted,
            reply_to=reply_to,
            attachment=upload if upload else "",
            voice=voice if voice else "",
            voice_duration_seconds=serializer.validated_data.get(
                "voice_duration_seconds"
            ),
        )
        _notify_new_message(message)
        _publish_message(message)
        message = _message_queryset(room).get(pk=message.pk)
        message._prefetched_reactions = []
        return Response(
            ChatMessageSerializer(message, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class ChatMessageDetailView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceMember]

    def get_message(self, room_id, message_id):
        room = _get_room_for_workspace(room_id, self.get_workspace(), self.request.user)
        message = get_object_or_404(_message_queryset(room), pk=message_id)
        return room, message

    def patch(self, request, room_id, message_id):
        room, message = self.get_message(room_id, message_id)
        if not can_edit_message(room, message, request.user):
            raise PermissionDenied("Cannot edit this message.")
        serializer = ChatMessageEditSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        is_encrypted = bool(serializer.validated_data.get("is_encrypted", message.is_encrypted))
        if is_encrypted and room.scope != ChatRoom.Scope.DM:
            raise ValidationError(
                {"is_encrypted": "E2E encryption is only supported for DMs."}
            )
        if message.is_encrypted and not is_encrypted:
            raise ValidationError({"is_encrypted": "Cannot downgrade an encrypted message."})
        message.body = serializer.validated_data["body"].strip()
        message.is_encrypted = is_encrypted
        message.edited_at = timezone.now()
        message.save(update_fields=["body", "is_encrypted", "edited_at"])
        _publish_message(message, "chat.message")
        message._prefetched_reactions = list(message.reactions.all())
        return Response(ChatMessageSerializer(message, context={"request": request}).data)

    def delete(self, request, room_id, message_id):
        room, message = self.get_message(room_id, message_id)
        if not can_delete_message(room, message, request.user):
            raise PermissionDenied("Cannot delete this message.")
        message.body = ""
        message.deleted_at = timezone.now()
        message.deleted_by = request.user
        message.save(update_fields=["body", "deleted_at", "deleted_by"])
        _publish_message(message, "chat.message")
        return Response(status=status.HTTP_204_NO_CONTENT)


class ChatMessageForwardView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceMember]

    def post(self, request, room_id, message_id):
        source_room = _get_room_for_workspace(
            room_id, self.get_workspace(), request.user
        )
        message = get_object_or_404(source_room.messages, pk=message_id)
        if message.is_deleted:
            raise ValidationError({"message_id": "Cannot forward a deleted message."})
        if message.is_encrypted:
            raise ValidationError({"message_id": "Cannot forward encrypted messages."})

        serializer = ChatForwardSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target = get_object_or_404(
            ChatRoom.objects.select_related(
                "project", "workspace", "project__workspace", "dm_user_low", "dm_user_high"
            ),
            pk=serializer.validated_data["target_chat_id"],
        )
        if not can_access(target, request.user):
            raise PermissionDenied("No access to target chat.")
        if not can_forward_into(target, request.user):
            raise PermissionDenied("Cannot post to the target chat.")
        if target.id == source_room.id:
            raise ValidationError({"target_chat_id": "Cannot forward to the same chat."})

        forwarded = ChatMessage.objects.create(
            room=target,
            author=request.user,
            body=message.body,
            forwarded_from=message,
            forward_source_label=source_room.display_label(),
        )
        if message.attachment:
            forwarded.attachment = message.attachment
            forwarded.save(update_fields=["attachment"])
        if message.voice:
            forwarded.voice = message.voice
            forwarded.voice_duration_seconds = message.voice_duration_seconds
            forwarded.save(update_fields=["voice", "voice_duration_seconds"])

        _notify_new_message(forwarded)
        _publish_message(forwarded)
        return Response(
            ChatMessageSerializer(forwarded, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class ChatReactionToggleView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceMember]

    def post(self, request, room_id, message_id):
        room = _get_room_for_workspace(room_id, self.get_workspace(), request.user)
        message = get_object_or_404(room.messages, pk=message_id)
        if message.is_deleted:
            raise ValidationError({"message_id": "Cannot react to a deleted message."})
        serializer = ChatReactionWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        kind = serializer.validated_data["kind"]
        emoji = serializer.validated_data.get("emoji") or ""
        gif_url = serializer.validated_data.get("gif_url") or ""
        existing = ChatReaction.objects.filter(
            message=message,
            user=request.user,
            kind=kind,
            emoji=emoji,
            gif_url=gif_url,
        ).first()
        if existing:
            existing.delete()
            toggled = "removed"
        else:
            ChatReaction.objects.create(
                message=message,
                user=request.user,
                kind=kind,
                emoji=emoji,
                gif_url=gif_url,
            )
            toggled = "added"
        message = _message_queryset(room).get(pk=message.pk)
        message._prefetched_reactions = list(message.reactions.all())
        _publish_message(message, "chat.message")
        return Response(
            {
                "toggled": toggled,
                "message": ChatMessageSerializer(
                    message, context={"request": request}
                ).data,
            }
        )


def _active_share_link(token: str) -> ProjectShareLink:
    link = (
        ProjectShareLink.objects.select_related("project", "project__workspace")
        .filter(token=token)
        .first()
    )
    if link is None or not link.is_active:
        raise NotFound("Share link not found or expired.")
    if not link.allow_chat:
        raise PermissionDenied("Chat is not enabled on this share link.")
    return link


class GuestChatView(APIView):
    """Public guest access to project chat via share link."""

    permission_classes = [AllowAny]
    authentication_classes = []
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get(self, request, token):
        link = _active_share_link(token)
        room = get_or_create_project_room(link.project)
        qs = _message_queryset(room)
        messages = list(qs[:50])
        for message in messages:
            message._prefetched_reactions = list(message.reactions.all())
        return Response(
            {
                "room": {
                    "id": room.id,
                    "status": room.status,
                    "label": room.display_label(),
                    "can_post": bool(
                        link.chat_can_post
                        and room.status == ChatRoom.Status.OPEN
                        and not room.is_archived
                    ),
                    "chat_can_post": link.chat_can_post,
                },
                "results": ChatMessageSerializer(
                    messages, many=True, context={"request": request}
                ).data,
            }
        )

    def post(self, request, token):
        link = _active_share_link(token)
        if not link.chat_can_post:
            raise PermissionDenied("Guest posting is disabled on this share link.")
        room = get_or_create_project_room(link.project)
        if room.status != ChatRoom.Status.OPEN or room.is_archived:
            raise PermissionDenied("Chat is not open for guest posts.")

        serializer = ChatMessageWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        body = (serializer.validated_data.get("body") or "").strip()
        guest_name = (serializer.validated_data.get("guest_name") or "Гость").strip()[
            :120
        ]
        upload = request.FILES.get("attachment")
        voice = request.FILES.get("voice")
        _validate_upload(upload, kind="attachment")
        _validate_upload(voice, kind="voice")
        reply_to_id = serializer.validated_data.get("reply_to")
        reply_to = None
        if reply_to_id:
            reply_to = get_object_or_404(room.messages, pk=reply_to_id)
        if not body and not upload and not voice:
            raise ValidationError(
                {"body": "Message body, attachment, or voice is required."}
            )

        message = ChatMessage.objects.create(
            room=room,
            author=None,
            guest_name=guest_name or "Гость",
            body=body,
            reply_to=reply_to,
            attachment=upload if upload else "",
            voice=voice if voice else "",
            voice_duration_seconds=serializer.validated_data.get(
                "voice_duration_seconds"
            ),
        )
        _notify_new_message(message)
        _publish_message(message)
        message = _message_queryset(room).get(pk=message.pk)
        message._prefetched_reactions = []
        return Response(
            ChatMessageSerializer(message, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class ChatCryptoMeView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceMember]

    def get(self, request):
        key = ChatUserCryptoKey.objects.filter(user=request.user).first()
        if key is None:
            return Response({"user_id": request.user.id, "public_jwk": None})
        return Response(ChatCryptoKeySerializer(key).data)

    def put(self, request):
        serializer = ChatCryptoKeyWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        key, _ = ChatUserCryptoKey.objects.update_or_create(
            user=request.user,
            defaults={"public_jwk": serializer.validated_data["public_jwk"]},
        )
        return Response(ChatCryptoKeySerializer(key).data)


class ChatCryptoUserView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceMember]

    def get(self, request, user_id):
        workspace = self.get_workspace()
        target = get_object_or_404(User, pk=user_id)
        if get_membership(workspace, target) is None:
            raise NotFound("User is not in this workspace.")
        key = ChatUserCryptoKey.objects.filter(user_id=user_id).first()
        if key is None:
            return Response({"user_id": user_id, "public_jwk": None})
        return Response(ChatCryptoKeySerializer(key).data)


class ChatRoomE2EKeysView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceMember]

    def get_dm_room(self, room_id):
        room = _get_room_for_workspace(room_id, self.get_workspace(), self.request.user)
        if room.scope != ChatRoom.Scope.DM:
            raise ValidationError({"room_id": "E2E keys are only for DM rooms."})
        return room

    def get(self, request, room_id):
        room = self.get_dm_room(room_id)
        wraps = room.key_wraps.select_related("user").all()
        return Response(
            {
                "room_id": room.id,
                "wraps": ChatRoomKeyWrapSerializer(wraps, many=True).data,
            }
        )

    def put(self, request, room_id):
        room = self.get_dm_room(room_id)
        serializer = ChatRoomKeyWrapWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        allowed = {room.dm_user_low_id, room.dm_user_high_id}
        wraps = serializer.validated_data["wraps"]
        for item in wraps:
            if item["user_id"] not in allowed:
                raise ValidationError({"wraps": "Wraps may only target DM participants."})
        saved = []
        for item in wraps:
            wrap, _ = ChatRoomKeyWrap.objects.update_or_create(
                room=room,
                user_id=item["user_id"],
                defaults={"wrapped_key": item["wrapped_key"]},
            )
            saved.append(wrap)
        return Response(
            {
                "room_id": room.id,
                "wraps": ChatRoomKeyWrapSerializer(saved, many=True).data,
            }
        )
