from django.urls import path

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
]
