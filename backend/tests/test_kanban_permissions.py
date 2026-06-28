import pytest
from rest_framework import status

from tests.factories import BoardFactory, CardFactory, ColumnFactory


@pytest.fixture
def other_board(other_user):
    workspace = other_user.workspace_memberships.first().workspace
    return workspace.boards.first()


@pytest.mark.django_db
def test_user_cannot_access_other_users_board(authenticated_client, other_board):
    response = authenticated_client.get(f"/api/boards/{other_board.id}/")
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_user_cannot_move_other_users_card(authenticated_client, other_user, user):
    other_board = other_user.workspace_memberships.first().workspace.boards.first()
    other_column = other_board.columns.first()
    other_card = CardFactory(column=other_column)

    own_column = user.workspace_memberships.first().workspace.boards.first().columns.first()

    response = authenticated_client.post(
        f"/api/cards/{other_card.id}/move/",
        {"column_id": own_column.id, "position": 0},
        format="json",
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_user_cannot_create_card_in_other_users_column(authenticated_client, other_user):
    other_column = other_user.workspace_memberships.first().workspace.boards.first().columns.first()
    response = authenticated_client.post(
        f"/api/columns/{other_column.id}/cards/",
        {"title": "Hack"},
        format="json",
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_user_cannot_delete_other_users_board(authenticated_client, other_board):
    response = authenticated_client.delete(f"/api/boards/{other_board.id}/")
    assert response.status_code == status.HTTP_404_NOT_FOUND
