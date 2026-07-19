import logging
from datetime import date, datetime

from django.db import transaction

from workspaces.models import WebhookDelivery, WebhookEndpoint

logger = logging.getLogger("fast_plan")

WEBHOOK_EVENTS = {
    "risk.created",
    "risk.updated",
    "risk.deleted",
    "deadline.upcoming",
}


def _json_safe(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def emit_webhook(
    workspace,
    event: str,
    payload: dict,
    *,
    dedupe_key: str | None = None,
) -> int:
    if event not in WEBHOOK_EVENTS:
        raise ValueError(f"Unsupported webhook event: {event}")
    endpoints = [
        endpoint
        for endpoint in WebhookEndpoint.objects.filter(
            workspace=workspace,
            is_active=True,
        )
        if event in endpoint.events
    ]
    deliveries = []
    for endpoint in endpoints:
        delivery_key = f"{endpoint.id}:{dedupe_key}" if dedupe_key else None
        defaults = {
            "endpoint": endpoint,
            "event": event,
            "payload": _json_safe(payload),
        }
        if delivery_key is None:
            delivery = WebhookDelivery.objects.create(**defaults)
            created = True
        else:
            delivery, created = WebhookDelivery.objects.get_or_create(
                dedupe_key=delivery_key,
                defaults=defaults,
            )
        if created:
            deliveries.append(delivery)

    def enqueue():
        from workspaces.tasks import deliver_webhook

        for delivery in deliveries:
            try:
                deliver_webhook.delay(delivery.id)
            except Exception:
                logger.exception(
                    "Failed to enqueue webhook delivery %s", delivery.id
                )

    transaction.on_commit(enqueue)
    return len(deliveries)
