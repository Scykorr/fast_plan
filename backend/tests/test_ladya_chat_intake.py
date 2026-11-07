"""Internal chat intake + agent connect (Telegram out of scope)."""

from rest_framework.test import APIClient

from chats.models import ChatMessage, ChatRoom
from chats.services import get_or_create_workspace_room
from delivery.models import AgentProfile
from ladya.defaults import get_or_create_ladya_settings
from ladya.models import IntakeRequest, Laboratory, Package
from notifications.models import Notification
from tests.factories import UserFactory
from workspaces.models import WorkspaceMember


def _enable(workspace):
    row, _ = get_or_create_ladya_settings(workspace)
    row.ladya_hub_enabled = True
    row.save(update_fields=["ladya_hub_enabled", "updated_at"])
    return row


def test_no_telegram_webhook_route(authenticated_client, workspace):
    _enable(workspace)
    # Old path must not accept Ladya intake anymore (removed from urls).
    resp = authenticated_client.post(
        "/api/ladya/telegram/any-secret/",
        {"message": {"text": "hi"}},
        format="json",
    )
    assert resp.status_code == 404
    assert IntakeRequest.objects.count() == 0


def test_ensure_lab_chat_and_intake_from_message(
    authenticated_client, workspace, user
):
    _enable(workspace)
    lab = Laboratory.objects.create(
        workspace=workspace,
        slug="central",
        title="Центральный ЛАД",
        kind=Laboratory.Kind.CENTRAL_LAD,
    )
    ensured = authenticated_client.post(
        f"/api/ladya/laboratories/{lab.id}/ensure-chat/",
        {},
        format="json",
    )
    assert ensured.status_code == 200
    assert ensured.data["chat_room_id"]
    assert ensured.data["open_path"] == "/portfolio?chat=1"
    lab.refresh_from_db()
    assert lab.chat_room_id == ensured.data["chat_room_id"]

    room = ChatRoom.objects.get(pk=lab.chat_room_id)
    msg = ChatMessage.objects.create(
        room=room,
        author=user,
        body="Нужна карта по пилоту",
    )
    caps = authenticated_client.get(
        f"/api/ladya/chat-rooms/{room.id}/capabilities/"
    )
    assert caps.status_code == 200
    assert caps.data["can_create_intake"] is True

    created = authenticated_client.post(
        "/api/ladya/intake/from-chat-message/",
        {"message_id": msg.id},
        format="json",
    )
    assert created.status_code == 201
    assert created.data["source"] == "internal_chat"
    assert created.data["body"].startswith("Нужна карта")
    assert Notification.objects.filter(
        user=user, dedupe_key=f"ladya-intake-{created.data['id']}-user-{user.id}"
    ).exists()


def test_intake_from_chat_rejects_foreign_workspace(
    authenticated_client, workspace, user
):
    _enable(workspace)
    other = UserFactory(email="other2@example.com", username="other2")
    other_ws = other.workspace_memberships.first().workspace
    room = get_or_create_workspace_room(other_ws)
    msg = ChatMessage.objects.create(room=room, author=other, body="x")
    bad = authenticated_client.post(
        "/api/ladya/intake/from-chat-message/",
        {"message_id": msg.id},
        format="json",
    )
    assert bad.status_code == 400


def test_package_notify_chat(authenticated_client, workspace, user):
    _enable(workspace)
    lab = Laboratory.objects.create(
        workspace=workspace,
        slug="private",
        title="Private",
        kind=Laboratory.Kind.PRIVATE_LAB,
    )
    authenticated_client.post(
        f"/api/ladya/laboratories/{lab.id}/ensure-chat/", {}, format="json"
    )
    pkg = authenticated_client.post(
        "/api/ladya/packages/",
        {"title": "Notice me", "to_laboratory": lab.id},
        format="json",
    )
    assert pkg.status_code == 201
    notice = authenticated_client.post(
        f"/api/ladya/packages/{pkg.data['id']}/notify-chat/",
        {},
        format="json",
    )
    assert notice.status_code == 201
    assert "PKG-" in notice.data["body"]
    assert ChatMessage.objects.filter(pk=notice.data["message_id"]).exists()


def test_agent_connect_wizard_and_reissue(authenticated_client, workspace, user):
    _enable(workspace)
    lab = Laboratory.objects.create(
        workspace=workspace,
        slug="lab0",
        title="Lab0",
        kind=Laboratory.Kind.LAB0,
    )
    created = authenticated_client.post(
        "/api/ladya/agents/",
        {
            "ladya_role": "quest",
            "display_name": "Quest bot",
            "laboratory": lab.id,
            "frontend_base_url": "http://localhost:5173",
        },
        format="json",
    )
    assert created.status_code == 201
    assert created.data["api_token_raw"]
    assert "Token" in created.data["connect_instruction"]
    assert created.data["ladya_role"] == "quest"
    agent_id = created.data["id"]
    listed = authenticated_client.get(f"/api/ladya/laboratories/{lab.id}/agents/")
    assert listed.status_code == 200
    assert any(row["id"] == agent_id for row in listed.data)
    # token not in list
    assert "api_token_raw" not in listed.data[0]

    reissued = authenticated_client.post(
        f"/api/ladya/agents/{agent_id}/reissue/",
        {"frontend_base_url": "http://localhost:5173"},
        format="json",
    )
    assert reissued.status_code == 200
    assert reissued.data["api_token_raw"]
    assert reissued.data["api_token_raw"] != created.data["api_token_raw"]

    viewer = UserFactory(email="viewer@example.com", username="viewer")
    WorkspaceMember.objects.create(
        workspace=workspace,
        user=viewer,
        role=WorkspaceMember.Role.VIEWER,
    )
    client = APIClient()
    client.force_authenticate(user=viewer)
    denied = client.post(
        "/api/ladya/agents/",
        {"ladya_role": "lad", "display_name": "nope"},
        format="json",
    )
    assert denied.status_code in (403, 400)


def test_web_form_intake_notifies(authenticated_client, workspace, user):
    _enable(workspace)
    resp = authenticated_client.post(
        "/api/ladya/intake/",
        {"body": "form intake", "contact": "@x"},
        format="json",
    )
    assert resp.status_code == 201
    assert Notification.objects.filter(
        user=user, title__contains="обращение"
    ).exists()
