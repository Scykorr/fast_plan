import hashlib
import hmac
import ipaddress
import json
import socket
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from celery import shared_task
from django.utils import timezone

from workspaces.models import WebhookDelivery


class _NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _validate_public_https_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("Webhook URL must use HTTPS.")
    for info in socket.getaddrinfo(parsed.hostname, parsed.port or 443):
        address = ipaddress.ip_address(info[4][0])
        if not address.is_global:
            raise ValueError("Webhook URL must resolve to a public address.")


@shared_task(bind=True, max_retries=3, name="workspaces.deliver_webhook")
def deliver_webhook(self, delivery_id: int):
    delivery = WebhookDelivery.objects.select_related("endpoint").get(pk=delivery_id)
    endpoint = delivery.endpoint
    if not endpoint.is_active:
        return {"status": "disabled"}

    delivery.attempt_count += 1
    body = json.dumps(
        {
            "id": delivery.id,
            "event": delivery.event,
            "created_at": delivery.created_at.isoformat(),
            "data": delivery.payload,
        },
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()
    signature = hmac.new(endpoint.secret.encode(), body, hashlib.sha256).hexdigest()
    try:
        _validate_public_https_url(endpoint.url)
        request = Request(
            endpoint.url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "Fast-Plan-Webhooks/1.0",
                "X-Fast-Plan-Event": delivery.event,
                "X-Fast-Plan-Signature": f"sha256={signature}",
            },
            method="POST",
        )
        with build_opener(_NoRedirectHandler()).open(request, timeout=10) as response:
            delivery.status_code = response.status
            delivery.response_body = response.read(2048).decode(errors="replace")
            delivery.delivered_at = timezone.now()
            delivery.error = ""
    except HTTPError as exc:
        delivery.status_code = exc.code
        delivery.response_body = exc.read(2048).decode(errors="replace")
        delivery.error = str(exc)
        if exc.code >= 500:
            delivery.save()
            raise self.retry(exc=exc, countdown=2**delivery.attempt_count)
    except (OSError, URLError) as exc:
        delivery.error = str(exc)
        delivery.save()
        raise self.retry(exc=exc, countdown=2**delivery.attempt_count)
    except ValueError as exc:
        delivery.error = str(exc)
    delivery.save()
    return {"status_code": delivery.status_code, "attempt": delivery.attempt_count}
