import pytest
from rest_framework import status

from workspaces.invitation_services import create_workspace_invitation
from workspaces.models import WorkspaceMember


@pytest.mark.django_db
def test_list_workspace_members(authenticated_client, user, workspace):
    response = authenticated_client.get("/api/workspace/members/")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) >= 1


@pytest.mark.django_db
def test_create_invitation(authenticated_client, user, workspace, settings, mailoutbox):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    settings.FRONTEND_BASE_URL = "http://frontend.test"
    response = authenticated_client.post(
        "/api/workspace/invitations/",
        {"email": "guest@example.com", "role": "editor"},
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert "token" in response.data
    assert len(mailoutbox) == 1
    assert "invite/" in mailoutbox[0].body

    # Re-invite upserts instead of IntegrityError.
    again = authenticated_client.post(
        "/api/workspace/invitations/",
        {"email": "guest@example.com", "role": "viewer"},
        format="json",
    )
    assert again.status_code == status.HTTP_201_CREATED
    assert again.data["role"] == "viewer"
    assert len(mailoutbox) == 2


@pytest.mark.django_db
def test_accept_invitation(authenticated_client, user, workspace, other_user):
    invitation = create_workspace_invitation(
        workspace, other_user.email, WorkspaceMember.Role.EDITOR, user
    )
    client = __import__("rest_framework.test", fromlist=["APIClient"]).APIClient()
    client.force_authenticate(user=other_user)
    response = client.post(f"/api/workspace/invitations/{invitation.token}/accept/")
    assert response.status_code == status.HTTP_200_OK
    assert WorkspaceMember.objects.filter(
        workspace=workspace, user=other_user
    ).exists()
    other_user.refresh_from_db()
    assert other_user.active_workspace_id == workspace.id


@pytest.mark.django_db
def test_me_includes_active_workspace(authenticated_client, user, workspace):
    response = authenticated_client.get("/api/auth/me/")
    assert response.status_code == status.HTTP_200_OK
    assert response.data["active_workspace_id"] == workspace.id
    assert response.data["active_workspace_name"] == workspace.name
