import pytest
from rest_framework import status

from tests.factories import ProjectFactory


@pytest.mark.django_db
def test_user_cannot_access_other_users_project(authenticated_client, other_user):
    other_project = ProjectFactory(
        workspace=other_user.workspace_memberships.first().workspace,
        name="Secret",
    )
    response = authenticated_client.get(f"/api/projects/{other_project.id}/")
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_user_cannot_delete_other_users_project(authenticated_client, other_user):
    other_project = ProjectFactory(
        workspace=other_user.workspace_memberships.first().workspace,
    )
    response = authenticated_client.delete(f"/api/projects/{other_project.id}/")
    assert response.status_code == status.HTTP_404_NOT_FOUND
