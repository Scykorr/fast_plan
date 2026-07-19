import pytest

from kanban.models import Board, Column
from workspaces.models import WorkspaceMember


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


@pytest.mark.django_db
def test_default_board_created_on_user_registration(api_client):
    api_client.post(
        "/api/auth/register/",
        {
            "email": "board@example.com",
            "username": "boarduser",
            "password": "securepass123",
        },
        format="json",
    )
    membership = WorkspaceMember.objects.get(user__email="board@example.com")
    board = Board.objects.get(workspace=membership.workspace)
    assert board.title == "Моя доска"
    columns = list(Column.objects.filter(board=board).order_by("position"))
    assert [column.title for column in columns] == [
        "К выполнению",
        "В работе",
        "Готово",
    ]
