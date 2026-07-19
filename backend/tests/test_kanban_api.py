import pytest
from rest_framework import status

from kanban.models import Board, Card, Column
from tests.factories import CardFactory


@pytest.fixture
def card(column):
    return CardFactory(column=column, title="My Card", position=column.cards.count())


@pytest.mark.django_db
def test_list_boards_returns_default_board(authenticated_client, user):
    response = authenticated_client.get("/api/boards/")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) >= 1
    assert response.data[0]["title"] == "Моя доска"


@pytest.mark.django_db
def test_board_detail_includes_columns(authenticated_client, board):
    response = authenticated_client.get(f"/api/boards/{board.id}/")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data["columns"]) == 3
    assert response.data["columns"][0]["title"] == "К выполнению"


@pytest.mark.django_db
def test_create_board(authenticated_client, workspace):
    response = authenticated_client.post(
        "/api/boards/",
        {"title": "Проект X", "position": 1},
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert Board.objects.filter(workspace=workspace, title="Проект X").exists()


@pytest.mark.django_db
def test_create_card(authenticated_client, column):
    response = authenticated_client.post(
        f"/api/columns/{column.id}/cards/",
        {"title": "Новая задача", "description": "Описание"},
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert Card.objects.filter(column=column, title="Новая задача").exists()


@pytest.mark.django_db
def test_update_card(authenticated_client, card):
    response = authenticated_client.patch(
        f"/api/cards/{card.id}/",
        {"title": "Обновлено"},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    card.refresh_from_db()
    assert card.title == "Обновлено"


@pytest.mark.django_db
def test_move_card_to_another_column(authenticated_client, board, column):
    target_column = board.columns.get(position=1)
    card = CardFactory(column=column, title="Move me", position=0)

    response = authenticated_client.post(
        f"/api/cards/{card.id}/move/",
        {"column_id": target_column.id, "position": 0},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    card.refresh_from_db()
    assert card.column_id == target_column.id
    assert card.position == 0


@pytest.mark.django_db
def test_reorder_card_within_same_column(authenticated_client, column):
    first = CardFactory(column=column, title="First", position=0)
    second = CardFactory(column=column, title="Second", position=1)

    response = authenticated_client.post(
        f"/api/cards/{second.id}/move/",
        {"column_id": column.id, "position": 0},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    first.refresh_from_db()
    second.refresh_from_db()
    assert second.position == 0
    assert first.position == 1
    assert first.column_id == column.id
    assert second.column_id == column.id


@pytest.mark.django_db
def test_delete_card(authenticated_client, card):
    card_id = card.id
    response = authenticated_client.delete(f"/api/cards/{card_id}/")
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not Card.objects.filter(pk=card_id).exists()


@pytest.mark.django_db
def test_move_column_reorders_positions(authenticated_client, board):
    columns = list(board.columns.order_by("position", "id"))
    first, second, third = columns

    response = authenticated_client.patch(
        f"/api/columns/{third.id}/",
        {"position": 0},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK

    first.refresh_from_db()
    second.refresh_from_db()
    third.refresh_from_db()
    assert third.position == 0
    assert first.position == 1
    assert second.position == 2


@pytest.mark.django_db
def test_update_column_title(authenticated_client, board):
    column = board.columns.first()
    response = authenticated_client.patch(
        f"/api/columns/{column.id}/",
        {"title": "Backlog"},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    column.refresh_from_db()
    assert column.title == "Backlog"


@pytest.mark.django_db
def test_delete_column_removes_cards(authenticated_client, board, column):
    CardFactory(column=column, title="Task 1", position=0)
    CardFactory(column=column, title="Task 2", position=1)
    column_id = column.id

    response = authenticated_client.delete(f"/api/columns/{column_id}/")
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not Column.objects.filter(pk=column_id).exists()
    assert not Card.objects.filter(column_id=column_id).exists()


@pytest.mark.django_db
def test_create_column(authenticated_client, board):
    response = authenticated_client.post(
        f"/api/boards/{board.id}/columns/",
        {"title": "На проверке"},
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert Column.objects.filter(board=board, title="На проверке").exists()


@pytest.mark.django_db
def test_board_cards_include_wbs_metadata(authenticated_client, board, column, workspace, user):
    from projects.models import Project, WBSNode
    from tracking.models import IssueStatus

    project = Project.objects.create(
        workspace=workspace, name="Linked", manager=user
    )
    root = project.wbs_nodes.filter(parent__isnull=True).first()
    status_obj = IssueStatus.objects.create(
        workspace=workspace, name="In Progress", position=0
    )
    node = WBSNode.objects.create(
        project=project,
        parent=root,
        title="WP",
        code="1.1",
        node_type=WBSNode.NodeType.WORK_PACKAGE,
        position=0,
        assignee=user,
        workflow_status=status_obj,
    )
    CardFactory(column=column, title="Synced", position=0, wbs_node=node)

    response = authenticated_client.get(f"/api/boards/{board.id}/")
    assert response.status_code == status.HTTP_200_OK
    cards = response.data["columns"][0]["cards"]
    synced = next(card for card in cards if card["title"] == "Synced")
    assert synced["wbs_node_id"] == node.id
    assert synced["assignee_id"] == user.id
    assert synced["workflow_status_id"] == status_obj.id
    assert synced["workflow_status_name"] == "In Progress"
