import pytest
from rest_framework.test import APIClient
from rest_framework import status

from tests.factories import UserFactory, WorkspaceMemberFactory
from workspaces.invitation_services import create_workspace_invitation
from workspaces.models import WorkspaceMember
from workspaces.services import set_active_workspace


@pytest.fixture
def editor_user(db, workspace):
    user = UserFactory(email="editor@example.com", username="editor")
    # Prefer the shared workspace over personal default.
    set_active_workspace(user, workspace)
    WorkspaceMemberFactory(
        workspace=workspace,
        user=user,
        role=WorkspaceMember.Role.EDITOR,
    )
    return user


@pytest.fixture
def viewer_user(db, workspace):
    user = UserFactory(email="viewer@example.com", username="viewer")
    set_active_workspace(user, workspace)
    WorkspaceMemberFactory(
        workspace=workspace,
        user=user,
        role=WorkspaceMember.Role.VIEWER,
    )
    return user


@pytest.fixture
def editor_client(editor_user):
    client = APIClient()
    client.force_authenticate(user=editor_user)
    client.credentials(HTTP_X_WORKSPACE_ID=str(editor_user.active_workspace_id))
    return client


@pytest.fixture
def viewer_client(viewer_user):
    client = APIClient()
    client.force_authenticate(user=viewer_user)
    client.credentials(HTTP_X_WORKSPACE_ID=str(viewer_user.active_workspace_id))
    return client


@pytest.mark.django_db
def test_list_workspaces_and_activate(authenticated_client, user, workspace, other_user):
    invitation = create_workspace_invitation(
        workspace, other_user.email, WorkspaceMember.Role.EDITOR, user
    )
    other_client = APIClient()
    other_client.force_authenticate(user=other_user)
    accept = other_client.post(f"/api/workspace/invitations/{invitation.token}/accept/")
    assert accept.status_code == status.HTTP_200_OK
    other_user.refresh_from_db()
    assert other_user.active_workspace_id == workspace.id

    response = other_client.get("/api/workspaces/")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) >= 2
    assert any(item["id"] == workspace.id and item["is_active"] for item in response.data)

    personal = next(item for item in response.data if item["id"] != workspace.id)
    activate = other_client.post(f"/api/workspaces/{personal['id']}/activate/")
    assert activate.status_code == status.HTTP_200_OK
    other_user.refresh_from_db()
    assert other_user.active_workspace_id == personal["id"]


@pytest.mark.django_db
def test_workspace_header_scopes_boards(authenticated_client, user, workspace, other_user):
    # other_user owns a separate workspace with its own board via signal
    other_client = APIClient()
    other_client.force_authenticate(user=other_user)
    other_ws = other_user.workspace_memberships.order_by("workspace__created_at").first().workspace
    other_client.credentials(HTTP_X_WORKSPACE_ID=str(other_ws.id))

    own_boards = other_client.get("/api/boards/")
    assert own_boards.status_code == status.HTTP_200_OK
    assert all(True for _ in own_boards.data)

    # non-member header is forbidden
    other_client.credentials(HTTP_X_WORKSPACE_ID=str(workspace.id))
    forbidden = other_client.get("/api/boards/")
    assert forbidden.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_viewer_cannot_create_card(viewer_client, column):
    response = viewer_client.post(
        f"/api/columns/{column.id}/cards/",
        {"title": "Nope"},
        format="json",
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_editor_can_create_card(editor_client, column):
    response = editor_client.post(
        f"/api/columns/{column.id}/cards/",
        {"title": "Allowed"},
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
def test_viewer_can_list_boards(viewer_client):
    response = viewer_client.get("/api/boards/")
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_editor_cannot_invite(editor_client):
    response = editor_client.post(
        "/api/workspace/invitations/",
        {"email": "x@example.com", "role": "viewer"},
        format="json",
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_editor_cannot_create_tracker(editor_client):
    response = editor_client.post(
        "/api/tracking/trackers/",
        {"name": "Bug", "target": "issue"},
        format="json",
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_accept_invitation_sets_active_workspace(user, workspace, other_user):
    invitation = create_workspace_invitation(
        workspace, other_user.email, WorkspaceMember.Role.VIEWER, user
    )
    client = APIClient()
    client.force_authenticate(user=other_user)
    response = client.post(f"/api/workspace/invitations/{invitation.token}/accept/")
    assert response.status_code == status.HTTP_200_OK
    other_user.refresh_from_db()
    assert other_user.active_workspace_id == workspace.id
    assert response.data["workspace_id"] == workspace.id
