import pytest
from django.conf import settings
from rest_framework import status

from workspaces.models import Workspace, WorkspaceMember


@pytest.mark.django_db
def test_register_creates_user_and_workspace(api_client):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    response = api_client.post(
        "/api/auth/register/",
        {
            "email": "newuser@example.com",
            "username": "newuser",
            "password": "securepass123",
            "first_name": "New",
            "last_name": "User",
        },
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["email"] == "newuser@example.com"

    user = User.objects.get(email="newuser@example.com")
    assert Workspace.objects.filter(owner=user).exists()
    assert WorkspaceMember.objects.filter(user=user, role=WorkspaceMember.Role.OWNER).exists()


@pytest.mark.django_db
def test_register_duplicate_email_fails(api_client, user):
    response = api_client.post(
        "/api/auth/register/",
        {
            "email": user.email,
            "username": "other",
            "password": "securepass123",
        },
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_login_sets_http_only_cookies(api_client, user):
    response = api_client.post(
        "/api/auth/login/",
        {"email": user.email, "password": "testpass123"},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    assert "access" not in response.data
    assert "refresh" not in response.data
    assert response.data["user"]["email"] == user.email
    assert settings.JWT_ACCESS_COOKIE in response.cookies
    assert settings.JWT_REFRESH_COOKIE in response.cookies
    assert response.cookies[settings.JWT_ACCESS_COOKIE]["httponly"] is True
    assert response.cookies[settings.JWT_REFRESH_COOKIE]["httponly"] is True


@pytest.mark.django_db
def test_login_invalid_credentials(api_client, user):
    response = api_client.post(
        "/api/auth/login/",
        {"email": user.email, "password": "wrongpassword"},
        format="json",
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_me_requires_authentication(api_client):
    response = api_client.get("/api/auth/me/")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_me_returns_current_user(authenticated_client, user):
    response = authenticated_client.get("/api/auth/me/")
    assert response.status_code == status.HTTP_200_OK
    assert response.data["email"] == user.email


@pytest.mark.django_db
def test_refresh_rotates_cookies(api_client, user):
    login = api_client.post(
        "/api/auth/login/",
        {"email": user.email, "password": "testpass123"},
        format="json",
    )
    old_refresh = login.cookies[settings.JWT_REFRESH_COOKIE].value
    csrf = api_client.get("/api/auth/csrf/")
    csrf_token = csrf.data["csrfToken"]
    response = api_client.post(
        "/api/auth/refresh/",
        {},
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    assert response.status_code == status.HTTP_200_OK
    assert settings.JWT_ACCESS_COOKIE in response.cookies
    assert settings.JWT_REFRESH_COOKIE in response.cookies
    assert response.cookies[settings.JWT_REFRESH_COOKIE].value != old_refresh


@pytest.mark.django_db
def test_cookie_auth_requires_csrf_for_mutations(user):
    from rest_framework.test import APIClient

    api_client = APIClient(enforce_csrf_checks=True)
    login = api_client.post(
        "/api/auth/login/",
        {"email": user.email, "password": "testpass123"},
        format="json",
    )
    assert login.status_code == status.HTTP_200_OK

    denied = api_client.post(
        "/api/boards/",
        {"title": "No CSRF", "position": 1},
        format="json",
    )
    assert denied.status_code == status.HTTP_403_FORBIDDEN

    csrf = api_client.get("/api/auth/csrf/")
    assert csrf.status_code == status.HTTP_200_OK
    csrf_token = csrf.data["csrfToken"]
    ok = api_client.post(
        "/api/boards/",
        {"title": "With CSRF", "position": 1},
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    assert ok.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
def test_logout_clears_cookies_and_blacklists(api_client, user):
    login = api_client.post(
        "/api/auth/login/",
        {"email": user.email, "password": "testpass123"},
        format="json",
    )
    csrf = api_client.get("/api/auth/csrf/")
    csrf_token = csrf.data["csrfToken"]
    logout = api_client.post(
        "/api/auth/logout/",
        {},
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    assert logout.status_code == status.HTTP_200_OK
    # Cookies deleted (empty / expired).
    access_cookie = logout.cookies.get(settings.JWT_ACCESS_COOKIE)
    refresh_cookie = logout.cookies.get(settings.JWT_REFRESH_COOKIE)
    assert access_cookie is not None
    assert refresh_cookie is not None

    refresh_again = api_client.post(
        "/api/auth/refresh/",
        {"refresh": login.cookies[settings.JWT_REFRESH_COOKIE].value},
        format="json",
    )
    assert refresh_again.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_password_forgot_sends_email_and_reset_works(api_client, user, settings, mailoutbox):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    settings.FRONTEND_BASE_URL = "http://frontend.test"

    forgot = api_client.post(
        "/api/auth/password/forgot/",
        {"email": user.email},
        format="json",
    )
    assert forgot.status_code == status.HTTP_200_OK
    assert len(mailoutbox) == 1
    body = mailoutbox[0].body
    assert "reset-password" in body

    from django.contrib.auth.tokens import PasswordResetTokenGenerator
    from django.utils.encoding import force_bytes
    from django.utils.http import urlsafe_base64_encode

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = PasswordResetTokenGenerator().make_token(user)
    reset = api_client.post(
        "/api/auth/password/reset/",
        {"uid": uid, "token": token, "new_password": "BrandNewPass99"},
        format="json",
    )
    assert reset.status_code == status.HTTP_200_OK
    user.refresh_from_db()
    assert user.check_password("BrandNewPass99")

    # Unknown email still returns 200 (no enumeration).
    again = api_client.post(
        "/api/auth/password/forgot/",
        {"email": "missing@example.com"},
        format="json",
    )
    assert again.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_password_change_requires_current(authenticated_client, user):
    bad = authenticated_client.post(
        "/api/auth/password/change/",
        {"current_password": "wrong", "new_password": "BrandNewPass99"},
        format="json",
    )
    assert bad.status_code == status.HTTP_400_BAD_REQUEST

    ok = authenticated_client.post(
        "/api/auth/password/change/",
        {"current_password": "testpass123", "new_password": "BrandNewPass99"},
        format="json",
    )
    assert ok.status_code == status.HTTP_200_OK
    user.refresh_from_db()
    assert user.check_password("BrandNewPass99")
