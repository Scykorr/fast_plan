import pytest
from django.contrib.auth import get_user_model
from rest_framework import status

from workspaces.models import Workspace, WorkspaceMember

User = get_user_model()


@pytest.mark.django_db
def test_register_creates_user_and_workspace(api_client):
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
def test_login_returns_tokens(api_client, user):
    response = api_client.post(
        "/api/auth/login/",
        {"email": user.email, "password": "testpass123"},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    assert "access" in response.data
    assert "refresh" in response.data


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
def test_refresh_token(api_client, user):
    login = api_client.post(
        "/api/auth/login/",
        {"email": user.email, "password": "testpass123"},
        format="json",
    )
    response = api_client.post(
        "/api/auth/refresh/",
        {"refresh": login.data["refresh"]},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    assert "access" in response.data
