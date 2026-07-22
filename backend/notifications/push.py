"""Web Push helpers (VAPID) for PWA notifications."""

from __future__ import annotations

import json
import logging

from django.conf import settings

logger = logging.getLogger("fast_plan")


def vapid_configured() -> bool:
    return bool(
        getattr(settings, "VAPID_PUBLIC_KEY", "").strip()
        and getattr(settings, "VAPID_PRIVATE_KEY", "").strip()
    )


def send_web_push(*, subscription, title: str, body: str = "", url: str = "/") -> bool:
    """Send a single Web Push. Returns False on failure; deletes gone subscriptions."""
    if not vapid_configured():
        return False
    try:
        from pywebpush import WebPushException, webpush
    except ImportError:
        logger.warning("pywebpush not installed; skip push")
        return False

    payload = json.dumps(
        {
            "title": title or "Fast Plan",
            "body": body or "",
            "url": url or "/",
        }
    )
    try:
        webpush(
            subscription_info={
                "endpoint": subscription.endpoint,
                "keys": {
                    "p256dh": subscription.p256dh,
                    "auth": subscription.auth,
                },
            },
            data=payload,
            vapid_private_key=settings.VAPID_PRIVATE_KEY,
            vapid_claims={
                "sub": getattr(settings, "VAPID_SUBJECT", "mailto:noreply@localhost"),
            },
        )
        return True
    except WebPushException as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        if status in (404, 410):
            subscription.delete()
            logger.info("Removed expired push subscription %s", subscription.id)
        else:
            logger.warning("Web push failed: %s", exc)
        return False
    except Exception as exc:  # noqa: BLE001
        logger.warning("Web push error: %s", exc)
        return False


def send_push_for_notification(notification) -> int:
    """Fan-out a Notification to the user's push subscriptions. Returns send count."""
    if not vapid_configured():
        return 0
    from notifications.models import PushSubscription

    sent = 0
    for sub in PushSubscription.objects.filter(user_id=notification.user_id):
        if send_web_push(
            subscription=sub,
            title=notification.title,
            body=notification.message or "",
            url=notification.link or "/",
        ):
            sent += 1
    return sent
