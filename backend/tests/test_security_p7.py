"""P7 security: TOTP 2FA, auth sessions, IP allowlist."""

import pyotp
import pytest
from django.utils import timezone
from rest_framework import status

from accounts.models import AuthSession
from accounts.security import create_pre_auth_token, ip_allowed


@pytest.mark.django_db
def test_login_requires_2fa_when_enabled(api_client, user):
    secret = pyotp.random_base32()
    user.totp_secret = secret
    user.totp_enabled_at = timezone.now()
    user.save(update_fields=["totp_secret", "totp_enabled_at"])

    response = api_client.post(
        "/api/auth/login/",
        {"email": user.email, "password": "testpass123"},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.data["requires_2fa"] is True
    assert response.data["pre_auth_token"]
    assert "fp_access" not in response.cookies


@pytest.mark.django_db
def test_2fa_verify_sets_cookies(api_client, user):
    secret = pyotp.random_base32()
    user.totp_secret = secret
    user.totp_enabled_at = timezone.now()
    user.save(update_fields=["totp_secret", "totp_enabled_at"])
    token = create_pre_auth_token(user.id)
    code = pyotp.TOTP(secret).now()

    response = api_client.post(
        "/api/auth/2fa/verify/",
        {"pre_auth_token": token, "code": code},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.data["user"]["email"] == user.email
    from django.conf import settings

    assert settings.JWT_ACCESS_COOKIE in response.cookies
    assert AuthSession.objects.filter(user=user, revoked_at__isnull=True).exists()


@pytest.mark.django_db
def test_2fa_setup_enable_disable(authenticated_client, user):
    setup = authenticated_client.post("/api/auth/2fa/setup/", {}, format="json")
    assert setup.status_code == status.HTTP_200_OK
    secret = setup.data["secret"]
    code = pyotp.TOTP(secret).now()

    enable = authenticated_client.post(
        "/api/auth/2fa/enable/", {"code": code}, format="json"
    )
    assert enable.status_code == status.HTTP_200_OK
    assert enable.data["user"]["is_totp_enabled"] is True
    assert len(enable.data["backup_codes"]) == 8

    user.refresh_from_db()
    disable_code = pyotp.TOTP(user.totp_secret).now()
    disable = authenticated_client.post(
        "/api/auth/2fa/disable/",
        {"password": "testpass123", "code": disable_code},
        format="json",
    )
    assert disable.status_code == status.HTTP_200_OK
    assert disable.data["user"]["is_totp_enabled"] is False


@pytest.mark.django_db
def test_auth_sessions_list_and_revoke(authenticated_client, user):
    # Login creates a session via cookies already present on authenticated_client
    AuthSession.objects.create(
        user=user,
        refresh_jti="other-jti-123",
        user_agent="test",
        ip_address="1.2.3.4",
    )
    listed = authenticated_client.get("/api/auth/sessions/")
    assert listed.status_code == status.HTTP_200_OK
    assert len(listed.data) >= 1

    other = AuthSession.objects.get(refresh_jti="other-jti-123")
    revoked = authenticated_client.post(
        f"/api/auth/sessions/{other.id}/revoke/", {}, format="json"
    )
    assert revoked.status_code == status.HTTP_200_OK
    other.refresh_from_db()
    assert other.revoked_at is not None


@pytest.mark.django_db
def test_workspace_ip_allowlist_blocks_request(api_client, user, workspace):
    workspace.ip_allowlist = ["203.0.113.10"]
    workspace.save(update_fields=["ip_allowlist"])

    login = api_client.post(
        "/api/auth/login/",
        {"email": user.email, "password": "testpass123"},
        format="json",
    )
    assert login.status_code == status.HTTP_200_OK

    blocked = api_client.get(
        "/api/workspace/dashboard/",
        HTTP_X_FORWARDED_FOR="198.51.100.1",
    )
    assert blocked.status_code == status.HTTP_403_FORBIDDEN

    allowed = api_client.get(
        "/api/workspace/dashboard/",
        HTTP_X_FORWARDED_FOR="203.0.113.10",
    )
    assert allowed.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_owner_can_patch_ip_allowlist(authenticated_client, workspace):
    response = authenticated_client.patch(
        "/api/workspace/ip-allowlist/",
        {"ip_allowlist": ["10.0.0.0/8", "127.0.0.1"]},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.data["ip_allowlist"] == ["10.0.0.0/8", "127.0.0.1"]
    workspace.refresh_from_db()
    assert workspace.ip_allowlist == ["10.0.0.0/8", "127.0.0.1"]


def test_ip_allowed_helper():
    assert ip_allowed("10.1.2.3", ["10.0.0.0/8"]) is True
    assert ip_allowed("11.0.0.1", ["10.0.0.0/8"]) is False
    assert ip_allowed("127.0.0.1", []) is True
