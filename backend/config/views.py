from django.conf import settings
from django.db import connection
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from config.version import get_product_version


def _check_database() -> str:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return "ok"
    except Exception:
        return "error"


def _check_redis() -> str:
    redis_url = getattr(settings, "REDIS_URL", "") or ""
    if not redis_url.strip():
        return "skipped"
    try:
        from django.core.cache import cache

        cache.set("health_check", "1", timeout=5)
        return "ok" if cache.get("health_check") == "1" else "error"
    except Exception:
        return "error"


def _check_email() -> dict:
    """Non-sending email config probe for extended health."""
    backend = settings.EMAIL_BACKEND or ""
    host = (getattr(settings, "EMAIL_HOST", "") or "").strip()
    is_console = "console" in backend.lower()
    is_locmem = "locmem" in backend.lower()
    configured = bool(host) and not is_console and not is_locmem
    require_verify = bool(getattr(settings, "REQUIRE_EMAIL_VERIFICATION", False))
    status = "ok"
    if require_verify and not configured:
        status = "warn"
    elif is_console or is_locmem:
        status = "dev"
    elif not configured:
        status = "unconfigured"
    return {
        "status": status,
        "configured": configured,
        "host": host or None,
        "backend": backend,
        "require_email_verification": require_verify,
    }


@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    data = {"status": "ok", "version": get_product_version()}
    if request.query_params.get("extended"):
        data["checks"] = {
            "database": _check_database(),
            "redis": _check_redis(),
            "email_backend": settings.EMAIL_BACKEND,
            "email": _check_email(),
            "celery_eager": getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False),
            "require_email_verification": bool(
                getattr(settings, "REQUIRE_EMAIL_VERIFICATION", False)
            ),
        }
    return Response(data)
