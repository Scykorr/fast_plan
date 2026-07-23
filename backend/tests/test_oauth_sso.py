"""P7 SSO OAuth tests (mocked token/userinfo exchange)."""

from unittest.mock import patch

import pytest
from django.core.cache import cache
from django.test import override_settings
from rest_framework import status

from accounts.models import SocialAccount, User


@pytest.mark.django_db
def test_oauth_providers_empty_by_default(api_client):
    response = api_client.get("/api/auth/oauth/providers/")
    assert response.status_code == status.HTTP_200_OK
    assert response.data == {"google": False, "microsoft": False}


@pytest.mark.django_db
@override_settings(
    OAUTH_GOOGLE_CLIENT_ID="gid",
    OAUTH_GOOGLE_CLIENT_SECRET="gsecret",
)
def test_oauth_google_disabled(api_client):
    """Google IdP is temporarily disabled even when credentials are set."""
    listed = api_client.get("/api/auth/oauth/providers/")
    assert listed.data["google"] is False
    response = api_client.get("/api/auth/oauth/google/")
    assert response.status_code == 400


@pytest.mark.django_db
@override_settings(
    OAUTH_MICROSOFT_CLIENT_ID="mid",
    OAUTH_MICROSOFT_CLIENT_SECRET="msecret",
    FRONTEND_BASE_URL="http://frontend.test",
)
def test_oauth_microsoft_start_redirects(api_client):
    response = api_client.get("/api/auth/oauth/microsoft/")
    assert response.status_code == 302
    assert "login.microsoftonline.com" in response["Location"]
    assert "state=" in response["Location"]


@pytest.mark.django_db
@override_settings(
    OAUTH_MICROSOFT_CLIENT_ID="mid",
    OAUTH_MICROSOFT_CLIENT_SECRET="msecret",
    FRONTEND_BASE_URL="http://frontend.test",
)
def test_oauth_microsoft_callback_creates_user(api_client):
    state = "teststate123"
    cache.set(
        f"fp:oauth:state:{state}",
        {"provider": "microsoft", "next": "/projects"},
        600,
    )

    def fake_http(url, *, data=None, headers=None):
        if "token" in url:
            return {"access_token": "atok"}
        return {
            "sub": "ms-uid-1",
            "email": "oauth.user@example.com",
            "given_name": "OAuth",
            "family_name": "User",
            "name": "OAuth User",
        }

    with patch("accounts.oauth_views._http_json", side_effect=fake_http):
        response = api_client.get(
            "/api/auth/oauth/microsoft/callback/",
            {"code": "authcode", "state": state},
        )

    assert response.status_code == 302
    assert response["Location"].startswith("http://frontend.test/projects")
    assert "fp_access" in response.cookies
    user = User.objects.get(email="oauth.user@example.com")
    assert SocialAccount.objects.filter(
        user=user, provider="microsoft", uid="ms-uid-1"
    ).exists()
    assert not user.has_usable_password()


@pytest.mark.django_db
@override_settings(
    OAUTH_MICROSOFT_CLIENT_ID="mid",
    OAUTH_MICROSOFT_CLIENT_SECRET="msecret",
    FRONTEND_BASE_URL="http://frontend.test",
)
def test_oauth_links_existing_email(api_client, user):
    state = "linkstate"
    cache.set(
        f"fp:oauth:state:{state}",
        {"provider": "microsoft", "next": "/"},
        600,
    )

    def fake_http(url, *, data=None, headers=None):
        if "token" in url:
            return {"access_token": "atok"}
        return {"sub": "ms-uid-2", "email": user.email}

    with patch("accounts.oauth_views._http_json", side_effect=fake_http):
        response = api_client.get(
            "/api/auth/oauth/microsoft/callback/",
            {"code": "authcode", "state": state},
        )

    assert response.status_code == 302
    assert SocialAccount.objects.filter(
        user=user, provider="microsoft", uid="ms-uid-2"
    ).exists()
    assert User.objects.filter(email=user.email).count() == 1


@pytest.mark.django_db
@override_settings(
    OAUTH_MICROSOFT_CLIENT_ID="mid",
    OAUTH_MICROSOFT_CLIENT_SECRET="msecret",
    FRONTEND_BASE_URL="http://frontend.test",
)
def test_oauth_invalid_state(api_client):
    response = api_client.get(
        "/api/auth/oauth/microsoft/callback/",
        {"code": "x", "state": "unknown"},
    )
    assert response.status_code == 302
    assert "oauth_error=invalid_state" in response["Location"]
