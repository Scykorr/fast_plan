import pytest
from django.core.exceptions import ImproperlyConfigured

from config.security import assert_production_secret, is_insecure_secret


def test_is_insecure_secret_detects_placeholders():
    assert is_insecure_secret("")
    assert is_insecure_secret("short")
    assert is_insecure_secret("django-insecure-dev-only-change-in-production")
    assert is_insecure_secret("change-me-in-production-please-now")
    assert not is_insecure_secret("a" * 48)


def test_assert_production_secret_fails_closed():
    with pytest.raises(ImproperlyConfigured):
        assert_production_secret("change-me-in-production-please-now", debug=False)


def test_assert_production_secret_allows_dev():
    assert_production_secret("django-insecure-dev-only-change-in-production", debug=True)


def test_debug_cookie_flags_match_environment():
    from config import settings as app_settings

    assert app_settings.JWT_COOKIE_SECURE == (not app_settings.DEBUG)
    assert app_settings.CSRF_COOKIE_SECURE == (not app_settings.DEBUG)
    assert app_settings.SESSION_COOKIE_SECURE == (not app_settings.DEBUG)
    if not app_settings.DEBUG:
        assert app_settings.SECURE_HSTS_SECONDS >= 1
        assert app_settings.SECURE_PROXY_SSL_HEADER == (
            "HTTP_X_FORWARDED_PROTO",
            "https",
        )
