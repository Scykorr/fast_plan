import pytest
from datetime import date
from rest_framework import status

from tests.factories import ContactFactory


@pytest.mark.django_db
def test_user_cannot_access_other_users_contact(authenticated_client, other_user):
    other_contact = ContactFactory(
        workspace=other_user.workspace_memberships.first().workspace,
        birthday=date(1990, 1, 1),
    )
    response = authenticated_client.get(f"/api/contacts/{other_contact.id}/")
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_user_cannot_delete_other_users_contact(authenticated_client, other_user):
    other_contact = ContactFactory(
        workspace=other_user.workspace_memberships.first().workspace,
        birthday=date(1990, 1, 1),
    )
    response = authenticated_client.delete(f"/api/contacts/{other_contact.id}/")
    assert response.status_code == status.HTTP_404_NOT_FOUND
