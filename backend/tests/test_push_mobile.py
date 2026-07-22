"""P7 Mobile: Web Push subscribe + VAPID helpers."""

from unittest.mock import patch

import pytest
from django.test import override_settings
from rest_framework import status

from notifications.models import Notification, PushSubscription
from notifications.push import send_push_for_notification, vapid_configured
from notifications.services import create_notification


@pytest.mark.django_db
def test_vapid_public_key_not_configured(authenticated_client):
    with override_settings(VAPID_PUBLIC_KEY="", VAPID_PRIVATE_KEY=""):
        response = authenticated_client.get("/api/push/vapid-public-key/")
    assert response.status_code == status.HTTP_200_OK
    assert response.data["configured"] is False


@pytest.mark.django_db
@override_settings(
    VAPID_PUBLIC_KEY="BTestPublicKey",
    VAPID_PRIVATE_KEY="TestPrivateKey",
    VAPID_SUBJECT="mailto:test@example.com",
)
def test_push_subscribe_and_unsubscribe(authenticated_client, user):
    response = authenticated_client.get("/api/push/vapid-public-key/")
    assert response.data["configured"] is True
    assert response.data["public_key"] == "BTestPublicKey"

    create = authenticated_client.post(
        "/api/push/subscribe/",
        {
            "endpoint": "https://push.example/sub/1",
            "keys": {"p256dh": "p256", "auth": "authkey"},
        },
        format="json",
    )
    assert create.status_code == status.HTTP_201_CREATED
    assert PushSubscription.objects.filter(
        user=user, endpoint="https://push.example/sub/1"
    ).exists()

    again = authenticated_client.post(
        "/api/push/subscribe/",
        {
            "endpoint": "https://push.example/sub/1",
            "keys": {"p256dh": "p256b", "auth": "authkey2"},
        },
        format="json",
    )
    assert again.status_code == status.HTTP_201_CREATED
    assert PushSubscription.objects.filter(user=user).count() == 1

    unsub = authenticated_client.post(
        "/api/push/unsubscribe/",
        {"endpoint": "https://push.example/sub/1"},
        format="json",
    )
    assert unsub.status_code == status.HTTP_200_OK
    assert unsub.data["deleted"] == 1
    assert not PushSubscription.objects.filter(
        endpoint="https://push.example/sub/1"
    ).exists()


@pytest.mark.django_db
@override_settings(
    VAPID_PUBLIC_KEY="BTestPublicKey",
    VAPID_PRIVATE_KEY="TestPrivateKey",
)
def test_create_notification_triggers_web_push(user, workspace):
    PushSubscription.objects.create(
        user=user,
        endpoint="https://push.example/sub/2",
        p256dh="p256",
        auth="auth",
    )
    with patch("notifications.push.send_web_push", return_value=True) as mock_send:
        notification, created = create_notification(
            user=user,
            notification_type=Notification.NotificationType.DEAL_TASK,
            title="Задача",
            message="Срок завтра",
            link="/deals",
            workspace=workspace,
        )
        assert created is True
        assert notification.id
        mock_send.assert_called_once()


@pytest.mark.django_db
@override_settings(
    VAPID_PUBLIC_KEY="BTestPublicKey",
    VAPID_PRIVATE_KEY="TestPrivateKey",
)
def test_send_push_for_notification_calls_send_web_push(user):
    sub = PushSubscription.objects.create(
        user=user,
        endpoint="https://push.example/sub/3",
        p256dh="p256",
        auth="auth",
    )
    notification = Notification.objects.create(
        user=user,
        notification_type=Notification.NotificationType.DEAL_TASK,
        title="Hello",
        message="World",
        link="/deals",
    )
    with patch("notifications.push.send_web_push", return_value=True) as mock_send:
        sent = send_push_for_notification(notification)
        assert sent == 1
        mock_send.assert_called_once()
        assert mock_send.call_args.kwargs["subscription"].id == sub.id


def test_vapid_configured_helper():
    with override_settings(VAPID_PUBLIC_KEY="", VAPID_PRIVATE_KEY=""):
        assert vapid_configured() is False
    with override_settings(VAPID_PUBLIC_KEY="a", VAPID_PRIVATE_KEY="b"):
        assert vapid_configured() is True
