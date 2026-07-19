import pytest
from rest_framework.test import APIClient

from tests.factories import CardFactory, UserFactory


@pytest.fixture(autouse=True)
def _isolated_media_root(tmp_path, settings):
    """Keep file uploads created during tests out of the real media/ dir."""
    settings.MEDIA_ROOT = tmp_path


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return UserFactory(email="alice@example.com", username="alice")


@pytest.fixture
def other_user(db):
    return UserFactory(email="bob@example.com", username="bob")


@pytest.fixture
def authenticated_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def workspace(user):
    return user.workspace_memberships.first().workspace


@pytest.fixture
def board(workspace):
    return workspace.boards.first()


@pytest.fixture
def column(board):
    return board.columns.first()


@pytest.fixture
def card(column):
    from tests.factories import CardFactory

    return CardFactory(column=column, title="My Card", position=column.cards.count())
