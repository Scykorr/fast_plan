"""P2 leftovers: roles + lab chat_room (Telegram removed for Ladya)."""

from chats.models import ChatRoom
from delivery.models import AgentProfile, DeliverySettings, LadyaAgentRole
from ladya.defaults import get_or_create_ladya_settings
from ladya.models import Laboratory, Package
from tests.factories import UserFactory


def _enable(workspace):
    row, _ = get_or_create_ladya_settings(workspace)
    row.ladya_hub_enabled = True
    row.save(update_fields=["ladya_hub_enabled", "updated_at"])
    return row


def test_agent_ladya_role_patch(authenticated_client, workspace, user):
    _enable(workspace)
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


def test_package_preferred_role_and_lab_chat_room(
    authenticated_client, workspace, user
):
    _enable(workspace)
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
    assert Package.objects.get(pk=created.data["id"]).preferred_role == "cartographer"


def test_lab_chat_room_rejects_foreign_workspace(
    authenticated_client, workspace
):
    _enable(workspace)
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
