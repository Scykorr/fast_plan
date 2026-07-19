import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


def absolute_frontend_url(path: str) -> str:
    base = getattr(settings, "FRONTEND_BASE_URL", "http://localhost:8080").rstrip("/")
    if not path:
        return base
    if path.startswith("http://") or path.startswith("https://"):
        return path
    return f"{base}/{path.lstrip('/')}"


def send_app_email(
    *,
    to: str,
    subject: str,
    template_base: str,
    context: dict | None = None,
) -> bool:
    """
    Render text+html templates and send email.
    Soft-fails on SMTP errors (logs and returns False) so callers like invite create
    do not 500 when mail is misconfigured.
    """
    ctx = dict(context or {})
    ctx.setdefault("frontend_base_url", absolute_frontend_url(""))
    try:
        text_body = render_to_string(f"{template_base}.txt", ctx)
        html_body = render_to_string(f"{template_base}.html", ctx)
        message = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[to],
        )
        message.attach_alternative(html_body, "text/html")
        message.send(fail_silently=False)
        return True
    except Exception:
        logger.exception("Failed to send email to %s (%s)", to, subject)
        return False
