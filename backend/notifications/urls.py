from django.urls import path

from notifications.push_views import (
    PushSubscribeView,
    PushUnsubscribeView,
    VapidPublicKeyView,
)
from notifications.views import (
    NotificationDetailView,
    NotificationListView,
    NotificationMarkAllReadView,
)

urlpatterns = [
    path("notifications/", NotificationListView.as_view(), name="notification-list"),
    path(
        "notifications/mark-all-read/",
        NotificationMarkAllReadView.as_view(),
        name="notification-mark-all-read",
    ),
    path(
        "notifications/<int:notification_id>/",
        NotificationDetailView.as_view(),
        name="notification-detail",
    ),
    path("push/vapid-public-key/", VapidPublicKeyView.as_view(), name="push-vapid-key"),
    path("push/subscribe/", PushSubscribeView.as_view(), name="push-subscribe"),
    path("push/unsubscribe/", PushUnsubscribeView.as_view(), name="push-unsubscribe"),
]
