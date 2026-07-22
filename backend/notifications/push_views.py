"""P7 Mobile: Web Push subscription API."""

from __future__ import annotations

from django.conf import settings
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from notifications.models import PushSubscription
from notifications.push import vapid_configured


class VapidPublicKeyView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not vapid_configured():
            return Response(
                {"configured": False, "public_key": ""},
                status=status.HTTP_200_OK,
            )
        return Response(
            {
                "configured": True,
                "public_key": settings.VAPID_PUBLIC_KEY.strip(),
            }
        )


class PushSubscribeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not vapid_configured():
            raise ValidationError({"detail": "Web Push is not configured on the server."})
        endpoint = (request.data.get("endpoint") or "").strip()
        keys = request.data.get("keys") or {}
        p256dh = (keys.get("p256dh") or request.data.get("p256dh") or "").strip()
        auth = (keys.get("auth") or request.data.get("auth") or "").strip()
        if not endpoint or not p256dh or not auth:
            raise ValidationError({"detail": "endpoint, keys.p256dh, keys.auth required."})
        ua = (request.META.get("HTTP_USER_AGENT") or "")[:400]
        sub, _ = PushSubscription.objects.update_or_create(
            endpoint=endpoint,
            defaults={
                "user": request.user,
                "p256dh": p256dh,
                "auth": auth,
                "user_agent": ua,
            },
        )
        return Response(
            {"id": sub.id, "endpoint": sub.endpoint},
            status=status.HTTP_201_CREATED,
        )


class PushUnsubscribeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        endpoint = (request.data.get("endpoint") or "").strip()
        if not endpoint:
            raise ValidationError({"endpoint": "Required."})
        deleted, _ = PushSubscription.objects.filter(
            user=request.user, endpoint=endpoint
        ).delete()
        return Response({"deleted": deleted})
