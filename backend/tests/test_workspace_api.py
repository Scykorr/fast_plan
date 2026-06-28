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
def test_create_invitation(authenticated_client, user, workspace):
    response = authenticated_client.post(
        "/api/workspace/invitations/",
        {"email": "guest@example.com", "role": "editor"},
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert "token" in response.data


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
