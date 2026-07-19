"""Production security helpers used by settings and tests."""

INSECURE_SECRET_MARKERS = (
    "insecure",
    "change-me",
    "change_me",
    "changeme",
    "django-insecure",
)


def is_insecure_secret(value: str | None) -> bool:
    normalized = (value or "").strip().lower()
    if not normalized or len(normalized) < 32:
        return True
    return any(marker in normalized for marker in INSECURE_SECRET_MARKERS)


def assert_production_secret(secret_key: str, *, debug: bool) -> None:
    from django.core.exceptions import ImproperlyConfigured

    if not debug and is_insecure_secret(secret_key):
        raise ImproperlyConfigured(
            "DJANGO_SECRET_KEY must be a strong secret when DJANGO_DEBUG=false."
        )
