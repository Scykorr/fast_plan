"""Agent work journal, person-to-person handoff, and my-tasks buckets."""

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from delivery.models import AgentProfile, DeliverySettings, DeliveryTask, TaskComment
from tests.factories import UserFactory
from tests.test_delivery_p9 import READY_FIELDS
from workspaces.models import WorkspaceMember

pytestmark = pytest.mark.django_db


@pytest.fixture
def enable_ops(workspace):
    row, _ = DeliverySettings.objects.get_or_create(workspace=workspace)
    row.agent_ops_enabled = True
    row.save(update_fields=["agent_ops_enabled", "updated_at"])
    return row


def test_dev_qa_owner_handoff_journal_and_inbox(
    authenticated_client, workspace, enable_ops, user
):
    qa = UserFactory(email="qa-agent@example.com", username="qaagent")
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
        display_name="QA Agent",
    )

    epic = authenticated_client.post(
        "/api/delivery/epics/",
        {"title": "CryptoGamp agent loop", "priority": "high"},
        format="json",
    )
    assert epic.status_code == status.HTTP_201_CREATED
    created = authenticated_client.post(
        "/api/delivery/tasks/",
        {**READY_FIELDS, "epic": epic.data["id"], "title": "API claim path"},
        format="json",
    )
    assert created.status_code == status.HTTP_201_CREATED
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
    claim = authenticated_client.post(
        f"/api/delivery/tasks/{task_id}/claim/",
        {"version": detail.data["version"]},
        format="json",
    )
    assert claim.data["status"] == "in_progress"

    note = authenticated_client.post(
        f"/api/delivery/tasks/{task_id}/comments/",
        {
            "kind": "result",
            "body": "Реализовано в ветке feature/agent-work-handoff, SHA abc123",
        },
        format="json",
    )
    assert note.status_code == status.HTTP_201_CREATED
    assert note.data["author_email"] == user.email
    assert note.data["kind"] == TaskComment.Kind.RESULT

    authenticated_client.patch(
        f"/api/delivery/tasks/{task_id}/",
        {
            "github_branch": "feature/agent-work-handoff",
            "github_commit": "abc123",
            "github_commits": ["abc123"],
            "github_repo": "org/cryptogamp",
            "implementation_summary": "Claim + handoff to QA",
        },
        format="json",
    )

    inbox = authenticated_client.get("/api/delivery/my-tasks/")
    assert inbox.status_code == status.HTTP_200_OK
    assert any(row["id"] == task_id for row in inbox.data["in_progress"])

    handoff = authenticated_client.post(
        f"/api/delivery/tasks/{task_id}/handoffs/",
        {
            "from_role": "backend",
            "to_role": "qa",
            "to_user": qa.id,
            "done_summary": "API готово, тесты зелёные",
            "reason": "Нужна проверка сценария claim→handoff",
            "expected_next_step": "Прогнать приёмочный путь и вернуть или отдать Owner",
            "branch_or_pr_url": "https://github.com/org/cryptogamp/pull/12",
        },
        format="json",
    )
    assert handoff.status_code == status.HTTP_201_CREATED
    assert handoff.data["task"]["status"] == "qa"
    assert handoff.data["task"]["assignee"] == qa.id
    assert handoff.data["task"]["previous_assignee"] == user.id
    assert handoff.data["handoff"]["reason"]
    assert handoff.data["handoff"]["to_user_email"] == qa.email

    qa_client = APIClient()
    qa_client.force_authenticate(user=qa)
    qa_client.credentials(HTTP_X_WORKSPACE_ID=str(workspace.id))
    qa_inbox = qa_client.get("/api/delivery/my-tasks/")
    assert any(row["id"] == task_id for row in qa_inbox.data["waiting_response"])

    finding = qa_client.post(
        f"/api/delivery/tasks/{task_id}/comments/",
        {"kind": "review_finding", "body": "Нет кейса на version conflict"},
        format="json",
    )
    assert finding.status_code == status.HTTP_201_CREATED

    back = qa_client.post(
        f"/api/delivery/tasks/{task_id}/handoffs/",
        {
            "from_role": "qa",
            "to_role": "backend",
            "to_user": user.id,
            "done_summary": "Нашёл пробел в тестах version conflict",
            "reason": "Нужна доработка",
            "expected_next_step": "Добавить тест conflict и вернуть в QA",
        },
        format="json",
    )
    assert back.status_code == status.HTTP_201_CREATED
    assert back.data["task"]["status"] == DeliveryTask.Status.NEEDS_REWORK
    assert back.data["task"]["assignee"] == user.id

    rework_inbox = authenticated_client.get("/api/delivery/my-tasks/")
    assert any(row["id"] == task_id for row in rework_inbox.data["returned_for_rework"])

    to_owner = authenticated_client.post(
        f"/api/delivery/tasks/{task_id}/handoffs/",
        {
            "from_role": "backend",
            "to_role": "owner",
            "done_summary": "Доработка внесена",
            "reason": "Готово к решению владельца",
            "expected_next_step": "Принять или вернуть",
        },
        format="json",
    )
    assert to_owner.status_code == status.HTTP_201_CREATED
    assert to_owner.data["task"]["status"] == DeliveryTask.Status.READY_FOR_OWNER

    history = authenticated_client.get(f"/api/delivery/tasks/{task_id}/history/")
    kinds = [e["kind"] for e in history.data["timeline"]]
    assert any(k.startswith("comment:") for k in kinds)
    assert "handoff" in kinds
    comments = authenticated_client.get(f"/api/delivery/tasks/{task_id}/comments/")
    authors = {row["author_email"] for row in comments.data}
    assert user.email in authors
    assert qa.email in authors
