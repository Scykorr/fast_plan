"""P2: Telegram→Intake, ladya_role, Laboratory.chat_room."""

import pytest
from rest_framework.test import APIClient

from chats.models import ChatRoom
from delivery.models import AgentProfile, DeliverySettings, DeliveryTask, LadyaAgentRole
from ladya.defaults import get_or_create_ladya_settings
from ladya.models import IntakeRequest, Laboratory, Package
from ladya.telegram import new_telegram_webhook_secret
from notifications.models import Notification
from tests.factories import UserFactory


@pytest.fixture
def enable_ladya(workspace):
    row, _ = get_or_create_ladya_settings(workspace)
    row.ladya_hub_enabled = True
    secret = new_telegram_webhook_secret()
    row.telegram_webhook_secret = secret
    row.save(
        update_fields=[
            "ladya_hub_enabled",
            "telegram_webhook_secret",
            "updated_at",
        ]
    )
    return row


def test_telegram_webhook_creates_intake_and_notifies(
    enable_ladya, workspace, user
):
    secret = enable_ladya.telegram_webhook_secret
    client = APIClient()
    update = {
        "update_id": 1,
        "message": {
            "message_id": 10,
            "text": "Нужна помощь с пакетом",
            "chat": {"id": 4242, "type": "private"},
            "from": {"id": 7, "username": "pilot_user"},
        },
    }
    resp = client.post(f"/api/ladya/telegram/{secret}/", update, format="json")
    assert resp.status_code == 200
    assert resp.data["ok"] is True
    assert resp.data["delivery_task_created"] is False
    intake_id = resp.data["intake_id"]
    assert intake_id

    intake = IntakeRequest.objects.get(pk=intake_id)
    assert intake.workspace_id == workspace.id
    assert intake.source == IntakeRequest.Source.TELEGRAM
    assert intake.status == IntakeRequest.Status.NEW
    assert intake.body.startswith("Нужна помощь")
    assert "@pilot_user" in intake.contact
    assert "chat:4242" in intake.contact
    assert DeliveryTask.objects.filter(workspace=workspace).count() == 0

    notes = Notification.objects.filter(
        user=user,
        workspace=workspace,
        dedupe_key=f"ladya-intake-{intake.id}-user-{user.id}",
    )
    assert notes.count() == 1
    assert "Telegram" in notes.first().title


def test_telegram_webhook_bad_secret_404(enable_ladya):
    client = APIClient()
    resp = client.post(
        "/api/ladya/telegram/wrong-secret/",
        {"message": {"text": "x", "chat": {"id": 1}, "from": {}}},
        format="json",
    )
    assert resp.status_code == 404
    assert IntakeRequest.objects.count() == 0


def test_telegram_webhook_empty_text_ok_no_intake(enable_ladya):
    secret = enable_ladya.telegram_webhook_secret
    client = APIClient()
    resp = client.post(
        f"/api/ladya/telegram/{secret}/",
        {"message": {"text": "  ", "chat": {"id": 1}, "from": {}}},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.data["intake_id"] is None
    assert IntakeRequest.objects.count() == 0


def test_telegram_webhook_disabled_hub_404(workspace, enable_ladya):
    enable_ladya.ladya_hub_enabled = False
    enable_ladya.save(update_fields=["ladya_hub_enabled", "updated_at"])
    client = APIClient()
    resp = client.post(
        f"/api/ladya/telegram/{enable_ladya.telegram_webhook_secret}/",
        {
            "message": {
                "text": "hi",
                "chat": {"id": 1},
                "from": {"username": "x"},
            }
        },
        format="json",
    )
    assert resp.status_code == 404


def test_rotate_telegram_secret(authenticated_client, enable_ladya):
    old = enable_ladya.telegram_webhook_secret
    resp = authenticated_client.patch(
        "/api/ladya/settings/",
        {"rotate_telegram_webhook_secret": True},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.data["telegram_webhook_secret_set"] is True
    assert resp.data["telegram_webhook_path"].startswith("/api/ladya/telegram/")
    enable_ladya.refresh_from_db()
    assert enable_ladya.telegram_webhook_secret
    assert enable_ladya.telegram_webhook_secret != old


def test_agent_ladya_role_patch(authenticated_client, workspace, enable_ladya, user):
    row, _ = DeliverySettings.objects.get_or_create(workspace=workspace)
    row.agent_ops_enabled = True
    row.save(update_fields=["agent_ops_enabled", "updated_at"])

    profile = AgentProfile.objects.create(
        workspace=workspace,
        user=user,
        role="backend",
        actor_type=AgentProfile.ActorType.AGENT,
        display_name="bot",
        is_service_account=True,
    )
    resp = authenticated_client.patch(
        f"/api/delivery/agents/{profile.id}/",
        {"ladya_role": LadyaAgentRole.LAD},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.data["ladya_role"] == "lad"
    profile.refresh_from_db()
    assert profile.ladya_role == "lad"


def test_package_preferred_role_and_lab_chat_room(
    authenticated_client, workspace, enable_ladya, user
):
    lab = Laboratory.objects.create(
        workspace=workspace,
        slug="central",
        title="Центральный",
        kind=Laboratory.Kind.CENTRAL_LAD,
    )
    room = ChatRoom.objects.create(
        scope=ChatRoom.Scope.WORKSPACE,
        workspace=workspace,
    )
    patched = authenticated_client.patch(
        f"/api/ladya/laboratories/{lab.id}/",
        {"chat_room": room.id},
        format="json",
    )
    assert patched.status_code == 200
    assert patched.data["chat_room"] == room.id

    created = authenticated_client.post(
        "/api/ladya/packages/",
        {
            "title": "Hint role",
            "to_laboratory": lab.id,
            "preferred_role": "cartographer",
        },
        format="json",
    )
    assert created.status_code == 201
    assert created.data["preferred_role"] == "cartographer"
    pkg = Package.objects.get(pk=created.data["id"])
    assert pkg.preferred_role == "cartographer"


def test_lab_chat_room_rejects_foreign_workspace(
    authenticated_client, workspace, enable_ladya
):
    other = UserFactory(email="other-ws@example.com", username="otherws")
    other_ws = other.workspace_memberships.first().workspace
    foreign_room = ChatRoom.objects.create(
        scope=ChatRoom.Scope.WORKSPACE,
        workspace=other_ws,
    )
    lab = Laboratory.objects.create(
        workspace=workspace,
        slug="lab0",
        title="Lab0",
        kind=Laboratory.Kind.LAB0,
    )
    bad = authenticated_client.patch(
        f"/api/ladya/laboratories/{lab.id}/",
        {"chat_room": foreign_room.id},
        format="json",
    )
    assert bad.status_code == 400
