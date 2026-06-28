import pytest

from workspaces.models import Workspace, WorkspaceMember


@pytest.mark.django_db
def test_workspace_created_on_user_registration(api_client):
    api_client.post(
        "/api/auth/register/",
        {
            "email": "workspace@example.com",
            "username": "workspaceuser",
            "password": "securepass123",
        },
        format="json",
    )
    membership = WorkspaceMember.objects.get(user__email="workspace@example.com")
    assert membership.role == WorkspaceMember.Role.OWNER
    assert membership.workspace.name == "Моё пространство"
    assert membership.workspace.owner.email == "workspace@example.com"
