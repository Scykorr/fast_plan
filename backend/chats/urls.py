from django.urls import path

from chats import views

urlpatterns = [
    path("chats/", views.ChatResolveView.as_view(), name="chat-resolve"),
    path("chats/mine/", views.ChatMineView.as_view(), name="chat-mine"),
    path("chats/dm/", views.ChatDmCreateView.as_view(), name="chat-dm-create"),
    path("chats/crypto/me/", views.ChatCryptoMeView.as_view(), name="chat-crypto-me"),
    path(
        "chats/crypto/users/<int:user_id>/",
        views.ChatCryptoUserView.as_view(),
        name="chat-crypto-user",
    ),
    path("chats/<int:room_id>/", views.ChatDetailView.as_view(), name="chat-detail"),
    path(
        "chats/<int:room_id>/e2e/",
        views.ChatRoomE2EKeysView.as_view(),
        name="chat-e2e-keys",
    ),
    path(
        "chats/<int:room_id>/mutes/",
        views.ChatMuteListCreateView.as_view(),
        name="chat-mutes",
    ),
    path(
        "chats/<int:room_id>/mutes/<int:user_id>/",
        views.ChatMuteDetailView.as_view(),
        name="chat-mute-detail",
    ),
    path(
        "chats/<int:room_id>/messages/",
        views.ChatMessageListCreateView.as_view(),
        name="chat-messages",
    ),
    path(
        "chats/<int:room_id>/messages/<int:message_id>/",
        views.ChatMessageDetailView.as_view(),
        name="chat-message-detail",
    ),
    path(
        "chats/<int:room_id>/messages/<int:message_id>/forward/",
        views.ChatMessageForwardView.as_view(),
        name="chat-forward",
    ),
    path(
        "chats/<int:room_id>/messages/<int:message_id>/reactions/",
        views.ChatReactionToggleView.as_view(),
        name="chat-reactions",
    ),
    path(
        "share/<str:token>/chat/",
        views.GuestChatView.as_view(),
        name="guest-chat",
    ),
]
