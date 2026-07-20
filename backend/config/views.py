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


@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    data = {"status": "ok", "version": get_product_version()}
    if request.query_params.get("extended"):
        data["checks"] = {
            "database": _check_database(),
            "redis": _check_redis(),
            "email_backend": settings.EMAIL_BACKEND,
            "celery_eager": getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False),
        }
    return Response(data)
