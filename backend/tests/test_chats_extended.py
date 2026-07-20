"""Extended chat features: DM, reply, reactions, edit/delete, guest, archive."""

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from chats.models import ChatMessage, ChatReaction, ChatRoom
from chats.services import archive_disabled_rooms, get_or_create_project_room
from projects.models import Project, ProjectMember, ProjectShareLink
from tests.factories import UserFactory, WorkspaceMemberFactory
from workspaces.models import WorkspaceMember
from workspaces.services import set_active_workspace


@pytest.fixture
def project_pair(workspace, user):
    project = Project.objects.create(
        workspace=workspace, name="Ext Chat", manager=user
    )
    ProjectMember.objects.create(
        project=project, user=user, role=ProjectMember.Role.MANAGER
    )
    peer = UserFactory(email="peer@example.com", username="peer")
    set_active_workspace(peer, workspace)
    WorkspaceMemberFactory(
        workspace=workspace, user=peer, role=WorkspaceMember.Role.EDITOR
    )
    ProjectMember.objects.create(
        project=project, user=peer, role=ProjectMember.Role.CONTRIBUTOR
    )
    return project, peer


@pytest.fixture
def peer_client(project_pair):
    _project, peer = project_pair
    client = APIClient()
    client.force_authenticate(user=peer)
    client.credentials(HTTP_X_WORKSPACE_ID=str(peer.active_workspace_id))
    return client


@pytest.mark.django_db
def test_dm_create_and_message(authenticated_client, project_pair, peer_client):
    _project, peer = project_pair
    created = authenticated_client.post(
        "/api/chats/dm/", {"user_id": peer.id}, format="json"
    )
    assert created.status_code == status.HTTP_201_CREATED
    assert created.data["scope"] == "dm"
    room_id = created.data["id"]

    posted = authenticated_client.post(
        f"/api/chats/{room_id}/messages/",
        {"body": "Privet"},
        format="json",
    )
    assert posted.status_code == status.HTTP_201_CREATED

    listed = peer_client.get(f"/api/chats/{room_id}/messages/")
    assert listed.status_code == status.HTTP_200_OK
    assert listed.data["results"][0]["body"] == "Privet"


@pytest.mark.django_db
def test_reply_and_reaction(authenticated_client, project_pair):
    project, _peer = project_pair
    room = authenticated_client.get(
        f"/api/chats/?scope=project&project_id={project.id}"
    ).data
    parent = authenticated_client.post(
        f"/api/chats/{room['id']}/messages/",
        {"body": "Parent"},
        format="json",
    ).data
    reply = authenticated_client.post(
        f"/api/chats/{room['id']}/messages/",
        {"body": "Child", "reply_to": parent["id"]},
        format="json",
    )
    assert reply.status_code == status.HTTP_201_CREATED
    assert reply.data["reply_to"] == parent["id"]

    reacted = authenticated_client.post(
        f"/api/chats/{room['id']}/messages/{parent['id']}/reactions/",
        {"emoji": "👍"},
        format="json",
    )
    assert reacted.status_code == status.HTTP_200_OK
    assert reacted.data["toggled"] == "added"
    assert ChatReaction.objects.filter(message_id=parent["id"]).count() == 1

    gif = authenticated_client.post(
        f"/api/chats/{room['id']}/messages/{parent['id']}/reactions/",
        {
            "kind": "gif",
            "gif_url": "https://media.giphy.com/media/111ebonMs90YLu/giphy.gif",
        },
        format="json",
    )
    assert gif.status_code == status.HTTP_200_OK
    assert gif.data["toggled"] == "added"
    groups = gif.data["message"]["reactions"]
    assert any(item["kind"] == "gif" for item in groups)


@pytest.mark.django_db
def test_dm_e2e_ciphertext_opaque(authenticated_client, project_pair, peer_client):
    _project, peer = project_pair
    created = authenticated_client.post(
        "/api/chats/dm/", {"user_id": peer.id}, format="json"
    )
    room_id = created.data["id"]
    assert created.data["e2e_enabled"] is True
    assert created.data["dm_peer_id"] == peer.id

    cipher = '{"v":1,"iv":"abc","ct":"secret-ciphertext"}'
    posted = authenticated_client.post(
        f"/api/chats/{room_id}/messages/",
        {"body": cipher, "is_encrypted": True},
        format="json",
    )
    assert posted.status_code == status.HTTP_201_CREATED
    assert posted.data["is_encrypted"] is True
    assert posted.data["body"] == cipher

    listed = peer_client.get(f"/api/chats/{room_id}/messages/")
    assert listed.data["results"][0]["body"] == cipher

    # Forward of encrypted message is forbidden
    other = authenticated_client.get("/api/chats/?scope=workspace").data
    blocked = authenticated_client.post(
        f"/api/chats/{room_id}/messages/{posted.data['id']}/forward/",
        {"target_chat_id": other["id"]},
        format="json",
    )
    assert blocked.status_code == status.HTTP_400_BAD_REQUEST

    # Crypto key publish + room wraps
    jwk = {
        "kty": "EC",
        "crv": "P-256",
        "x": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
        "y": "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",
    }
    me = authenticated_client.put(
        "/api/chats/crypto/me/", {"public_jwk": jwk}, format="json"
    )
    assert me.status_code == status.HTTP_200_OK
    assert me.data["public_jwk"]["crv"] == "P-256"

    author_id = me.data["user_id"]
    peer_view = peer_client.get(f"/api/chats/crypto/users/{author_id}/")
    assert peer_view.status_code == status.HTTP_200_OK
    assert peer_view.data["public_jwk"]["x"] == jwk["x"]

    wraps = authenticated_client.put(
        f"/api/chats/{room_id}/e2e/",
        {
            "wraps": [
                {"user_id": author_id, "wrapped_key": "wrap-a"},
                {"user_id": peer.id, "wrapped_key": "wrap-b"},
            ]
        },
        format="json",
    )
    assert wraps.status_code == status.HTTP_200_OK
    assert len(wraps.data["wraps"]) == 2


@pytest.mark.django_db
def test_crypto_recovery_backup(authenticated_client, project_pair):
    jwk = {
        "kty": "EC",
        "crv": "P-256",
        "x": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
        "y": "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",
    }
    saved = authenticated_client.put(
        "/api/chats/crypto/me/",
        {
            "public_jwk": jwk,
            "recovery_blob": '{"v":1,"iv":"x","ct":"y"}',
            "recovery_salt": "c2FsdA==",
        },
        format="json",
    )
    assert saved.status_code == status.HTTP_200_OK
    assert saved.data["has_recovery"] is True

    me = authenticated_client.get("/api/chats/crypto/me/")
    assert me.data["recovery_blob"].startswith("{")
    assert me.data["recovery_salt"] == "c2FsdA=="


@pytest.mark.django_db
def test_dm_encrypted_attachment_allowed(authenticated_client, project_pair):
    from django.core.files.uploadedfile import SimpleUploadedFile

    _project, peer = project_pair
    created = authenticated_client.post(
        "/api/chats/dm/", {"user_id": peer.id}, format="json"
    )
    room_id = created.data["id"]
    cipher_meta = '{"v":1,"iv":"aa","ct":"meta"}'
    upload = SimpleUploadedFile(
        "voice.bin", b"\x00" * 32, content_type="application/octet-stream"
    )
    posted = authenticated_client.post(
        f"/api/chats/{room_id}/messages/",
        {
            "body": cipher_meta,
            "is_encrypted": True,
            "attachment": upload,
        },
        format="multipart",
    )
    assert posted.status_code == status.HTTP_201_CREATED
    assert posted.data["is_encrypted"] is True
    assert posted.data["attachment_url"]


@pytest.mark.django_db
def test_gif_reaction_rejects_bad_host(authenticated_client, project_pair):
    project, _peer = project_pair
    room = authenticated_client.get(
        f"/api/chats/?scope=project&project_id={project.id}"
    ).data
    parent = authenticated_client.post(
        f"/api/chats/{room['id']}/messages/",
        {"body": "Parent"},
        format="json",
    ).data
    bad = authenticated_client.post(
        f"/api/chats/{room['id']}/messages/{parent['id']}/reactions/",
        {"kind": "gif", "gif_url": "https://evil.example/x.gif"},
        format="json",
    )
    assert bad.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_moderator_edit_delete(authenticated_client, project_pair, peer_client):
    project, _peer = project_pair
    room = authenticated_client.get(
        f"/api/chats/?scope=project&project_id={project.id}"
    ).data
    msg = peer_client.post(
        f"/api/chats/{room['id']}/messages/",
        {"body": "Oops"},
        format="json",
    ).data
    edited = authenticated_client.patch(
        f"/api/chats/{room['id']}/messages/{msg['id']}/",
        {"body": "Fixed by admin"},
        format="json",
    )
    assert edited.status_code == status.HTTP_200_OK
    assert edited.data["body"] == "Fixed by admin"
    assert edited.data["edited_at"]

    deleted = authenticated_client.delete(
        f"/api/chats/{room['id']}/messages/{msg['id']}/"
    )
    assert deleted.status_code == status.HTTP_204_NO_CONTENT
    assert ChatMessage.objects.get(pk=msg["id"]).is_deleted


@pytest.mark.django_db
def test_guest_chat_via_share_link(authenticated_client, project_pair):
    project, _peer = project_pair
    link = ProjectShareLink.objects.create(
        project=project,
        token="guest-chat-token",
        created_by=project.manager,
        allow_chat=True,
        chat_can_post=True,
    )
    client = APIClient()
    listed = client.get(f"/api/share/{link.token}/chat/")
    assert listed.status_code == status.HTTP_200_OK
    assert listed.data["room"]["can_post"] is True

    posted = client.post(
        f"/api/share/{link.token}/chat/",
        {"body": "Hello from guest", "guest_name": "Alice"},
        format="json",
    )
    assert posted.status_code == status.HTTP_201_CREATED
    assert posted.data["guest_name"] == "Alice"
    assert posted.data["author_id"] is None


@pytest.mark.django_db
def test_archive_disabled_rooms_task(workspace, user):
    project = Project.objects.create(
        workspace=workspace, name="Archive Me", manager=user
    )
    room = get_or_create_project_room(project)
    room.status = ChatRoom.Status.DISABLED
    room.status_changed_at = timezone.now() - timedelta(days=31)
    room.save(update_fields=["status", "status_changed_at"])
    count = archive_disabled_rooms(older_than_days=30)
    assert count == 1
    room.refresh_from_db()
    assert room.status == ChatRoom.Status.ARCHIVED
    assert room.archived_at is not None
