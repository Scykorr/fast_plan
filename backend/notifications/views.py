from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from notifications.models import Notification
from notifications.serializers import NotificationSerializer
from workspaces.services import get_request_workspace


class NotificationPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class NotificationListView(APIView):
    def get(self, request):
        notifications = Notification.objects.filter(user=request.user)
        workspace = get_request_workspace(request)
        if workspace is not None:
            notifications = notifications.filter(workspace=workspace)
        unread = request.query_params.get("unread")
        if unread == "true":
            notifications = notifications.filter(is_read=False)
        paginator = NotificationPagination()
        page = paginator.paginate_queryset(notifications, request, view=self)
        serializer = NotificationSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


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


class NotificationMarkAllReadView(APIView):
    def post(self, request):
        notifications = Notification.objects.filter(user=request.user, is_read=False)
        workspace = get_request_workspace(request)
        if workspace is not None:
            notifications = notifications.filter(workspace=workspace)
        updated = notifications.update(is_read=True)
        return Response({"updated": updated})
