"""P5 chats: ACL, moderation, messages, forward."""

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from chats.models import ChatMessage, ChatRoom, ChatRoomMute
from chats.services import can_post, get_or_create_project_room, is_moderator
from projects.models import Project, ProjectMember
from tests.factories import UserFactory, WorkspaceMemberFactory
from workspaces.models import WorkspaceMember
from workspaces.services import set_active_workspace


@pytest.fixture
def project(workspace, user):
    return Project.objects.create(
        workspace=workspace,
        name="Chat Project",
        manager=user,
    )


@pytest.fixture
def project_with_contributor(workspace, user):
    project = Project.objects.create(
        workspace=workspace,
        name="Chat Project",
        manager=user,
    )
    ProjectMember.objects.create(
        project=project,
        user=user,
        role=ProjectMember.Role.MANAGER,
    )
    contributor = UserFactory(email="contrib@example.com", username="contrib")
    set_active_workspace(contributor, workspace)
    WorkspaceMemberFactory(
        workspace=workspace,
        user=contributor,
        role=WorkspaceMember.Role.EDITOR,
    )
    ProjectMember.objects.create(
        project=project,
        user=contributor,
        role=ProjectMember.Role.CONTRIBUTOR,
    )
    return project, contributor


@pytest.fixture
def contrib_client(project_with_contributor):
    _project, contributor = project_with_contributor
    client = APIClient()
    client.force_authenticate(user=contributor)
    client.credentials(HTTP_X_WORKSPACE_ID=str(contributor.active_workspace_id))
    return client


@pytest.mark.django_db
def test_resolve_project_chat_lazy_create(authenticated_client, project):
    response = authenticated_client.get(
        f"/api/chats/?scope=project&project_id={project.id}"
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.data["scope"] == "project"
    assert response.data["project_id"] == project.id
    assert response.data["status"] == "open"
    assert response.data["can_post"] is True
    assert response.data["is_moderator"] is True
    assert ChatRoom.objects.filter(project=project).count() == 1


@pytest.mark.django_db
def test_resolve_workspace_chat(authenticated_client, workspace):
    response = authenticated_client.get("/api/chats/?scope=workspace")
    assert response.status_code == status.HTTP_200_OK
    assert response.data["scope"] == "workspace"
    assert response.data["workspace_id"] == workspace.id


@pytest.mark.django_db
def test_post_and_list_messages(authenticated_client, project):
    room = authenticated_client.get(
        f"/api/chats/?scope=project&project_id={project.id}"
    ).data
    room_id = room["id"]
    created = authenticated_client.post(
        f"/api/chats/{room_id}/messages/",
        {"body": "Hello team"},
        format="json",
    )
    assert created.status_code == status.HTTP_201_CREATED
    assert created.data["body"] == "Hello team"

    listed = authenticated_client.get(f"/api/chats/{room_id}/messages/")
    assert listed.status_code == status.HTTP_200_OK
    assert len(listed.data["results"]) == 1


@pytest.mark.django_db
def test_disabled_blocks_post(authenticated_client, project_with_contributor, contrib_client):
    project, _contributor = project_with_contributor
    room = authenticated_client.get(
        f"/api/chats/?scope=project&project_id={project.id}"
    ).data
    room_id = room["id"]
    patched = authenticated_client.patch(
        f"/api/chats/{room_id}/",
        {"status": "disabled"},
        format="json",
    )
    assert patched.status_code == status.HTTP_200_OK
    assert patched.data["status"] == "disabled"

    denied = contrib_client.post(
        f"/api/chats/{room_id}/messages/",
        {"body": "Nope"},
        format="json",
    )
    assert denied.status_code == status.HTTP_403_FORBIDDEN

    # Moderator also cannot post when disabled
    denied_mod = authenticated_client.post(
        f"/api/chats/{room_id}/messages/",
        {"body": "Moder"},
        format="json",
    )
    assert denied_mod.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_announcements_only_moderator_posts(
    authenticated_client, project_with_contributor, contrib_client
):
    project, _contributor = project_with_contributor
    room = authenticated_client.get(
        f"/api/chats/?scope=project&project_id={project.id}"
    ).data
    room_id = room["id"]
    authenticated_client.patch(
        f"/api/chats/{room_id}/",
        {"status": "announcements"},
        format="json",
    )
    denied = contrib_client.post(
        f"/api/chats/{room_id}/messages/",
        {"body": "Contributor try"},
        format="json",
    )
    assert denied.status_code == status.HTTP_403_FORBIDDEN

    ok = authenticated_client.post(
        f"/api/chats/{room_id}/messages/",
        {"body": "Announcement"},
        format="json",
    )
    assert ok.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
def test_mute_blocks_contributor(
    authenticated_client, project_with_contributor, contrib_client
):
    project, contributor = project_with_contributor
    room = authenticated_client.get(
        f"/api/chats/?scope=project&project_id={project.id}"
    ).data
    room_id = room["id"]
    muted = authenticated_client.post(
        f"/api/chats/{room_id}/mutes/",
        {"user_id": contributor.id, "reason": "spam"},
        format="json",
    )
    assert muted.status_code == status.HTTP_201_CREATED
    assert ChatRoomMute.objects.filter(room_id=room_id, user=contributor).exists()

    denied = contrib_client.post(
        f"/api/chats/{room_id}/messages/",
        {"body": "Muted"},
        format="json",
    )
    assert denied.status_code == status.HTTP_403_FORBIDDEN

    authenticated_client.delete(f"/api/chats/{room_id}/mutes/{contributor.id}/")
    ok = contrib_client.post(
        f"/api/chats/{room_id}/messages/",
        {"body": "Unmuted"},
        format="json",
    )
    assert ok.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
def test_forward_between_rooms(authenticated_client, project_with_contributor, workspace):
    project, _contributor = project_with_contributor
    other = Project.objects.create(
        workspace=workspace,
        name="Other Project",
        manager=project.manager,
    )
    ProjectMember.objects.create(
        project=other,
        user=project.manager,
        role=ProjectMember.Role.MANAGER,
    )

    source = authenticated_client.get(
        f"/api/chats/?scope=project&project_id={project.id}"
    ).data
    target = authenticated_client.get(
        f"/api/chats/?scope=project&project_id={other.id}"
    ).data
    msg = authenticated_client.post(
        f"/api/chats/{source['id']}/messages/",
        {"body": "Forward me"},
        format="json",
    ).data

    forwarded = authenticated_client.post(
        f"/api/chats/{source['id']}/messages/{msg['id']}/forward/",
        {"target_chat_id": target["id"]},
        format="json",
    )
    assert forwarded.status_code == status.HTTP_201_CREATED
    assert forwarded.data["body"] == "Forward me"
    assert forwarded.data["forward_source_label"]
    assert ChatMessage.objects.filter(room_id=target["id"]).count() == 1


@pytest.mark.django_db
def test_non_member_cannot_access_chat(api_client, project):
    stranger = UserFactory(email="stranger@example.com", username="stranger")
    api_client.force_authenticate(user=stranger)
    response = api_client.get(f"/api/chats/?scope=project&project_id={project.id}")
    assert response.status_code in {
        status.HTTP_403_FORBIDDEN,
        status.HTTP_404_NOT_FOUND,
    }


@pytest.mark.django_db
def test_services_moderator_and_can_post(project, user):
    room = get_or_create_project_room(project)
    assert is_moderator(room, user)
    assert can_post(room, user)
    room.status = ChatRoom.Status.DISABLED
    room.save(update_fields=["status"])
    assert not can_post(room, user)


@pytest.mark.django_db
def test_mine_lists_rooms(authenticated_client, project):
    authenticated_client.get(f"/api/chats/?scope=project&project_id={project.id}")
    authenticated_client.get("/api/chats/?scope=workspace")
    response = authenticated_client.get("/api/chats/mine/")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) >= 2
