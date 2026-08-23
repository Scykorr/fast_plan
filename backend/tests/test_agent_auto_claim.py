"""Auto-claim on assign/handoff for service accounts and delivery webhooks."""

import pytest
from rest_framework import status

from delivery.models import AgentProfile, DeliverySettings, DeliveryTask
from tests.factories import UserFactory
from tests.test_delivery_p9 import READY_FIELDS
from workspaces.models import WebhookDelivery, WebhookEndpoint, WorkspaceMember

pytestmark = pytest.mark.django_db


@pytest.fixture
def enable_ops(workspace):
    row, _ = DeliverySettings.objects.get_or_create(workspace=workspace)
    row.agent_ops_enabled = True
    row.save(update_fields=["agent_ops_enabled", "updated_at"])
    return row


def test_assign_to_service_account_auto_claims(
    authenticated_client, workspace, enable_ops, user
):
    backend = UserFactory(email="backend-svc@example.com", username="backendsvc")
    WorkspaceMember.objects.get_or_create(
        workspace=workspace,
        user=backend,
        defaults={"role": WorkspaceMember.Role.EDITOR},
    )
    AgentProfile.objects.create(
        workspace=workspace,
        user=backend,
        role="backend",
        actor_type=AgentProfile.ActorType.AGENT,
        is_service_account=True,
        auto_claim_on_assign=True,
        display_name="Backend Svc",
    )

    epic = authenticated_client.post(
        "/api/delivery/epics/",
        {"title": "Auto claim epic", "priority": "high"},
        format="json",
    )
    assert epic.status_code == status.HTTP_201_CREATED
    created = authenticated_client.post(
        "/api/delivery/tasks/",
        {**READY_FIELDS, "epic": epic.data["id"], "title": "Auto claim task"},
        format="json",
    )
    assert created.status_code == status.HTTP_201_CREATED
    task_id = created.data["id"]
    authenticated_client.post(
        f"/api/delivery/tasks/{task_id}/status/",
        {"status": "ready"},
        format="json",
    )

    assigned = authenticated_client.post(
        f"/api/delivery/tasks/{task_id}/assign/",
        {"assignee": backend.id, "assignee_role": "backend"},
        format="json",
    )
    assert assigned.status_code == status.HTTP_200_OK
    assert assigned.data["status"] == DeliveryTask.Status.IN_PROGRESS
    assert assigned.data["assignee"] == backend.id

    task = DeliveryTask.objects.get(pk=task_id)
    assert task.status == DeliveryTask.Status.IN_PROGRESS
    assert task.assignee_id == backend.id


def test_handoff_to_service_account_auto_claims(
    authenticated_client, workspace, enable_ops, user
):
    qa = UserFactory(email="qa-svc@example.com", username="qasvc")
    WorkspaceMember.objects.get_or_create(
        workspace=workspace,
        user=qa,
        defaults={"role": WorkspaceMember.Role.EDITOR},
    )
    AgentProfile.objects.create(
        workspace=workspace,
        user=user,
        role="backend",
        actor_type=AgentProfile.ActorType.AGENT,
        display_name="Backend Agent",
    )
    AgentProfile.objects.create(
        workspace=workspace,
        user=qa,
        role="qa",
        actor_type=AgentProfile.ActorType.AGENT,
        is_service_account=True,
        auto_claim_on_assign=True,
        display_name="QA Svc",
    )

    epic = authenticated_client.post(
        "/api/delivery/epics/",
        {"title": "Handoff auto claim", "priority": "normal"},
        format="json",
    )
    created = authenticated_client.post(
        "/api/delivery/tasks/",
        {**READY_FIELDS, "epic": epic.data["id"], "title": "Handoff path"},
        format="json",
    )
    task_id = created.data["id"]
    authenticated_client.post(
        f"/api/delivery/tasks/{task_id}/status/",
        {"status": "ready"},
        format="json",
    )
    authenticated_client.post(
        f"/api/delivery/tasks/{task_id}/assign/",
        {"assignee": user.id, "assignee_role": "backend"},
        format="json",
    )
    detail = authenticated_client.get(f"/api/delivery/tasks/{task_id}/")
    authenticated_client.post(
        f"/api/delivery/tasks/{task_id}/claim/",
        {"version": detail.data["version"]},
        format="json",
    )

    handoff = authenticated_client.post(
        f"/api/delivery/tasks/{task_id}/handoffs/",
        {
            "from_role": "backend",
            "to_role": "qa",
            "to_user": qa.id,
            "done_summary": "Ready for QA",
            "reason": "Please verify",
            "expected_next_step": "Run acceptance path",
        },
        format="json",
    )
    assert handoff.status_code == status.HTTP_201_CREATED
    assert handoff.data["task"]["assignee"] == qa.id
    assert handoff.data["task"]["status"] == DeliveryTask.Status.IN_PROGRESS


def test_assign_emits_delivery_webhook(
    authenticated_client, workspace, enable_ops, user
):
    backend = UserFactory(email="backend-wh@example.com", username="backendwh")
    WorkspaceMember.objects.get_or_create(
        workspace=workspace,
        user=backend,
        defaults={"role": WorkspaceMember.Role.EDITOR},
    )
    AgentProfile.objects.create(
        workspace=workspace,
        user=backend,
        role="backend",
        actor_type=AgentProfile.ActorType.AGENT,
        is_service_account=True,
        auto_claim_on_assign=True,
    )
    WebhookEndpoint.objects.create(
        workspace=workspace,
        name="agent-runner",
        url="https://runner.example/hook",
        secret="secret",
        events=["delivery.task.assigned"],
        created_by=user,
    )

    epic = authenticated_client.post(
        "/api/delivery/epics/",
        {"title": "Webhook epic", "priority": "normal"},
        format="json",
    )
    created = authenticated_client.post(
        "/api/delivery/tasks/",
        {**READY_FIELDS, "epic": epic.data["id"], "title": "Webhook task"},
        format="json",
    )
    task_id = created.data["id"]
    authenticated_client.post(
        f"/api/delivery/tasks/{task_id}/status/",
        {"status": "ready"},
        format="json",
    )
    authenticated_client.post(
        f"/api/delivery/tasks/{task_id}/assign/",
        {"assignee": backend.id, "assignee_role": "backend"},
        format="json",
    )

    delivery = WebhookDelivery.objects.filter(event="delivery.task.assigned").first()
    assert delivery is not None
    assert delivery.payload["task"]["id"] == task_id
    assert delivery.payload["auto_claimed"] is True
