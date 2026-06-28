from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from notifications.models import Notification
from notifications.serializers import NotificationSerializer


class NotificationListView(APIView):
    def get(self, request):
        from notifications.signals import check_birthday_reminders

        check_birthday_reminders(request.user)
        notifications = Notification.objects.filter(user=request.user)
        unread = request.query_params.get("unread")
        if unread == "true":
            notifications = notifications.filter(is_read=False)
        return Response(NotificationSerializer(notifications[:50], many=True).data)


class NotificationDetailView(APIView):
    def patch(self, request, notification_id):
        notification = get_object_or_404(
            Notification.objects.filter(user=request.user),
            pk=notification_id,
        )
        if "is_read" in request.data:
            notification.is_read = bool(request.data["is_read"])
            notification.save(update_fields=["is_read"])
        return Response(NotificationSerializer(notification).data)

    def delete(self, request, notification_id):
        notification = get_object_or_404(
            Notification.objects.filter(user=request.user),
            pk=notification_id,
        )
        notification.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
