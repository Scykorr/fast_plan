"""P9 Agent Ops delivery API tests (TZ end-to-end)."""

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from delivery.models import (
    AgentProfile,
    DeliverySettings,
    DeliveryTask,
    TaskDependency,
)

User = get_user_model()

READY_FIELDS = {
    "title": "Implement claim API",
    "business_outcome": "Agents can claim Ready tasks atomically",
    "context": "Agent Ops delivery layer",
    "scope_in": "claim endpoint + optimistic lock",
    "scope_out": "crypto payouts",
    "ready_criterion": "fields filled + docs linked",
    "done_criterion": "tests green",
    "expected_checks": "pytest delivery",
    "result_artifact": "PR + green CI",
    "assignee_role": "backend",
    "next_role": "qa",
    "canon_url": "https://example.com/canon",
    "architecture_url": "https://example.com/arch",
    "planning_doc_url": "https://example.com/plan",
    "acceptance_url": "https://example.com/acceptance",
}


@pytest.fixture
def enable_ops(workspace):
    row, _ = DeliverySettings.objects.get_or_create(workspace=workspace)
    row.agent_ops_enabled = True
    row.save(update_fields=["agent_ops_enabled", "updated_at"])
    return row


@pytest.mark.django_db
def test_settings_flag_gates_api(authenticated_client, workspace):
    denied = authenticated_client.get("/api/delivery/epics/")
    assert denied.status_code == status.HTTP_403_FORBIDDEN

    patch = authenticated_client.patch(
        "/api/delivery/settings/",
        {"agent_ops_enabled": True},
        format="json",
    )
    assert patch.status_code == status.HTTP_200_OK
    assert patch.data["agent_ops_enabled"] is True

    ok = authenticated_client.get("/api/delivery/epics/")
    assert ok.status_code == status.HTTP_200_OK
    assert ok.data == []


@pytest.mark.django_db
def test_full_ready_gate_and_history(
    authenticated_client, workspace, enable_ops, user
):
    epic = authenticated_client.post(
        "/api/delivery/epics/",
        {"title": "Agent Ops MVP", "priority": "high"},
        format="json",
    )
    assert epic.status_code == status.HTTP_201_CREATED

    sprint = authenticated_client.post(
        "/api/delivery/sprints/",
        {"name": "Sprint 1", "status": "active"},
        format="json",
    )
    assert sprint.status_code == status.HTTP_201_CREATED

    bare = authenticated_client.post(
        "/api/delivery/tasks/",
        {"title": "Bare task", "epic": epic.data["id"], "sprint": sprint.data["id"]},
        format="json",
    )
    assert bare.status_code == status.HTTP_201_CREATED
    assert bare.data["status"] == "draft"
    assert "context" in bare.data["ready_missing"]

    fail_ready = authenticated_client.post(
        f"/api/delivery/tasks/{bare.data['id']}/status/",
        {"status": "ready"},
        format="json",
    )
    assert fail_ready.status_code == status.HTTP_400_BAD_REQUEST

    filled = authenticated_client.patch(
        f"/api/delivery/tasks/{bare.data['id']}/",
        READY_FIELDS,
        format="json",
    )
    assert filled.status_code == status.HTTP_200_OK
    assert filled.data["ready_missing"] == []

    ready = authenticated_client.post(
        f"/api/delivery/tasks/{bare.data['id']}/status/",
        {"status": "ready"},
        format="json",
    )
    assert ready.status_code == status.HTTP_200_OK
    assert ready.data["status"] == "ready"

    history = authenticated_client.get(
        f"/api/delivery/tasks/{bare.data['id']}/history/"
    )
    assert history.status_code == status.HTTP_200_OK
    assert any(
        row["to_status"] == "ready" for row in history.data["status_history"]
    )
    assert any(row["field"] == "context" for row in history.data["field_history"])


@pytest.mark.django_db
def test_claim_blocker_handoff_deps_queue(
    authenticated_client, workspace, enable_ops, user
):
    other = authenticated_client.post(
        "/api/delivery/tasks/",
        {**READY_FIELDS, "title": "Dep task"},
        format="json",
    )
    create = authenticated_client.post(
        "/api/delivery/tasks/",
        READY_FIELDS,
        format="json",
    )
    task_id = create.data["id"]
    dep = authenticated_client.post(
        f"/api/delivery/tasks/{task_id}/dependencies/",
        {"depends_on": other.data["id"]},
        format="json",
    )
    assert dep.status_code == status.HTTP_201_CREATED
    assert TaskDependency.objects.filter(task_id=task_id).count() == 1

    # Satisfy dependency so claim is allowed
    authenticated_client.post(
        f"/api/delivery/tasks/{other.data['id']}/status/",
        {"status": "ready"},
        format="json",
    )
    other_detail = authenticated_client.get(
        f"/api/delivery/tasks/{other.data['id']}/"
    )
    authenticated_client.post(
        f"/api/delivery/tasks/{other.data['id']}/claim/",
        {"version": other_detail.data["version"]},
        format="json",
    )
    authenticated_client.post(
        f"/api/delivery/tasks/{other.data['id']}/status/",
        {"status": "review"},
        format="json",
    )
    authenticated_client.post(
        f"/api/delivery/tasks/{other.data['id']}/status/",
        {"status": "done"},
        format="json",
    )

    authenticated_client.post(
        f"/api/delivery/tasks/{task_id}/status/",
        {"status": "ready"},
        format="json",
    )
    detail = authenticated_client.get(f"/api/delivery/tasks/{task_id}/")
    claim = authenticated_client.post(
        f"/api/delivery/tasks/{task_id}/claim/",
        {"version": detail.data["version"]},
        format="json",
    )
    assert claim.status_code == status.HTTP_200_OK
    assert claim.data["status"] == "in_progress"
    assert claim.data["assignee"] == user.id

    hist = authenticated_client.get(f"/api/delivery/tasks/{task_id}/history/")
    statuses = [r["to_status"] for r in hist.data["status_history"]]
    assert "assigned" in statuses
    assert "in_progress" in statuses
    assert any(e["kind"] == "status" for e in hist.data["timeline"])
    assert any(
        row["field"] == "assignee" for row in hist.data["field_history"]
    )

    conflict = authenticated_client.post(
        f"/api/delivery/tasks/{task_id}/claim/",
        {"version": 1},
        format="json",
    )
    assert conflict.status_code == status.HTTP_400_BAD_REQUEST

    blocker = authenticated_client.post(
        f"/api/delivery/tasks/{task_id}/blockers/",
        {"title": "Waiting on docs", "needs_owner_decision": True},
        format="json",
    )
    assert blocker.status_code == status.HTTP_201_CREATED
    blocked = authenticated_client.get(f"/api/delivery/tasks/{task_id}/")
    assert blocked.data["status"] == "blocked"

    resolve = authenticated_client.post(
        f"/api/delivery/tasks/{task_id}/blockers/{blocker.data['id']}/resolve/",
        {"note": "docs linked"},
        format="json",
    )
    assert resolve.status_code == status.HTTP_200_OK
    assert resolve.data["resolved_at"]

    after = authenticated_client.get(f"/api/delivery/tasks/{task_id}/")
    assert after.data["status"] == "in_progress"

    handoff = authenticated_client.post(
        f"/api/delivery/tasks/{task_id}/handoffs/",
        {
            "from_role": "backend",
            "to_role": "qa",
            "done_summary": "API done, tests green",
            "left_summary": "QA checklist",
            "branch_or_pr_url": "https://github.com/org/repo/pull/1",
            "checks_url": "https://github.com/org/repo/actions",
            "open_questions": "none",
        },
        format="json",
    )
    assert handoff.status_code == status.HTTP_201_CREATED
    assert handoff.data["task"]["status"] == "qa"
    assert handoff.data["task"]["assignee_role"] == "qa"

    queue = authenticated_client.get("/api/delivery/queue/?role=qa&status=qa")
    assert queue.status_code == status.HTTP_200_OK
    assert any(row["id"] == task_id for row in queue.data)

    snippet = authenticated_client.get(f"/api/delivery/tasks/{task_id}/pr-snippet/")
    assert snippet.status_code == status.HTTP_200_OK
    assert "Fast Plan task" in snippet.data["markdown"]


@pytest.mark.django_db
def test_agent_cannot_change_epic_priority_or_close(
    authenticated_client, workspace, enable_ops, user
):
    AgentProfile.objects.create(
        workspace=workspace,
        user=user,
        role="backend",
        actor_type=AgentProfile.ActorType.AGENT,
        display_name="BE Agent",
    )
    epic = authenticated_client.post(
        "/api/delivery/epics/",
        {"title": "E1", "priority": "critical"},
        format="json",
    )
    assert epic.status_code == status.HTTP_201_CREATED
    assert epic.data["priority"] == "normal"

    denied = authenticated_client.patch(
        f"/api/delivery/epics/{epic.data['id']}/",
        {"priority": "critical"},
        format="json",
    )
    assert denied.status_code == status.HTTP_403_FORBIDDEN

    close = authenticated_client.patch(
        f"/api/delivery/epics/{epic.data['id']}/",
        {"status": "done"},
        format="json",
    )
    assert close.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_blocker_cancel_requires_reason(authenticated_client, enable_ops):
    create = authenticated_client.post(
        "/api/delivery/tasks/", READY_FIELDS, format="json"
    )
    task_id = create.data["id"]
    authenticated_client.post(
        f"/api/delivery/tasks/{task_id}/status/", {"status": "ready"}, format="json"
    )
    detail = authenticated_client.get(f"/api/delivery/tasks/{task_id}/")
    authenticated_client.post(
        f"/api/delivery/tasks/{task_id}/claim/",
        {"version": detail.data["version"]},
        format="json",
    )
    blocker = authenticated_client.post(
        f"/api/delivery/tasks/{task_id}/blockers/",
        {"title": "temp"},
        format="json",
    )
    bad = authenticated_client.post(
        f"/api/delivery/tasks/{task_id}/blockers/{blocker.data['id']}/cancel/",
        {},
        format="json",
    )
    assert bad.status_code == status.HTTP_400_BAD_REQUEST
    ok = authenticated_client.post(
        f"/api/delivery/tasks/{task_id}/blockers/{blocker.data['id']}/cancel/",
        {"reason": "duplicate"},
        format="json",
    )
    assert ok.status_code == status.HTTP_200_OK
    assert ok.data["cancelled_at"]


@pytest.mark.django_db
def test_service_account_provision(authenticated_client, enable_ops):
    resp = authenticated_client.post(
        "/api/delivery/agents/service-accounts/",
        {"role": "backend", "display_name": "BE Bot"},
        format="json",
    )
    assert resp.status_code == status.HTTP_201_CREATED
    assert resp.data["is_service_account"] is True
    assert resp.data["api_token_raw"].startswith("fp_")
    assert AgentProfile.objects.filter(is_service_account=True).exists()


@pytest.mark.django_db
def test_github_webhook_updates_task_and_reviews(workspace, enable_ops):
    task = DeliveryTask.objects.create(
        workspace=workspace,
        title="PR task",
        github_repo="org/repo",
        github_pr_number=42,
        **{k: v for k, v in READY_FIELDS.items() if k != "title"},
    )
    client = APIClient()
    resp = client.post(
        "/api/delivery/webhooks/github/",
        {
            "action": "submitted",
            "pull_request": {
                "number": 42,
                "state": "open",
                "html_url": "https://github.com/org/repo/pull/42",
                "head": {"ref": "feat/x", "sha": "abc123"},
            },
            "review": {"state": "changes_requested", "body": "Please fix tests"},
            "repository": {"full_name": "org/repo"},
        },
        format="json",
        HTTP_X_GITHUB_EVENT="pull_request_review",
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["updated"] == 1
    task.refresh_from_db()
    assert task.github_pr_state == "open"
    assert "Please fix tests" in task.github_review_notes


@pytest.mark.django_db
def test_idempotency_key_on_create(authenticated_client, enable_ops):
    headers = {"HTTP_IDEMPOTENCY_KEY": "agent-create-1"}
    first = authenticated_client.post(
        "/api/delivery/tasks/",
        {"title": "Idempotent"},
        format="json",
        **headers,
    )
    assert first.status_code == status.HTTP_201_CREATED
    second = authenticated_client.post(
        "/api/delivery/tasks/",
        {"title": "Idempotent"},
        format="json",
        **headers,
    )
    assert second.status_code == status.HTTP_201_CREATED
    assert second.data["id"] == first.data["id"]
    assert DeliveryTask.objects.filter(title="Idempotent").count() == 1


@pytest.mark.django_db
def test_dependency_blocks_claim_and_cycle(
    authenticated_client, enable_ops
):
    dep = authenticated_client.post(
        "/api/delivery/tasks/",
        {**READY_FIELDS, "title": "Unfinished dep"},
        format="json",
    )
    main = authenticated_client.post(
        "/api/delivery/tasks/",
        {**READY_FIELDS, "title": "Main"},
        format="json",
    )
    authenticated_client.post(
        f"/api/delivery/tasks/{main.data['id']}/dependencies/",
        {"depends_on": dep.data["id"]},
        format="json",
    )
    cycle = authenticated_client.post(
        f"/api/delivery/tasks/{dep.data['id']}/dependencies/",
        {"depends_on": main.data["id"]},
        format="json",
    )
    assert cycle.status_code == status.HTTP_400_BAD_REQUEST

    authenticated_client.post(
        f"/api/delivery/tasks/{main.data['id']}/status/",
        {"status": "ready"},
        format="json",
    )
    detail = authenticated_client.get(f"/api/delivery/tasks/{main.data['id']}/")
    claim = authenticated_client.post(
        f"/api/delivery/tasks/{main.data['id']}/claim/",
        {"version": detail.data["version"]},
        format="json",
    )
    assert claim.status_code == status.HTTP_400_BAD_REQUEST
    assert "dependencies" in str(claim.data).lower()


@pytest.mark.django_db
def test_assign_and_subtask_comment(
    authenticated_client, enable_ops, user
):
    create = authenticated_client.post(
        "/api/delivery/tasks/", READY_FIELDS, format="json"
    )
    task_id = create.data["id"]
    authenticated_client.post(
        f"/api/delivery/tasks/{task_id}/status/",
        {"status": "ready"},
        format="json",
    )
    assigned = authenticated_client.post(
        f"/api/delivery/tasks/{task_id}/assign/",
        {"assignee": user.id, "assignee_role": "backend"},
        format="json",
    )
    assert assigned.status_code == status.HTTP_200_OK
    assert assigned.data["status"] == "assigned"
    assert assigned.data["assignee"] == user.id

    sub = authenticated_client.post(
        f"/api/delivery/tasks/{task_id}/subtasks/",
        {"title": "Write tests", "expected_artifact": "pytest"},
        format="json",
    )
    assert sub.status_code == status.HTTP_201_CREATED
    patched = authenticated_client.patch(
        f"/api/delivery/tasks/{task_id}/subtasks/{sub.data['id']}/",
        {"status": "done"},
        format="json",
    )
    assert patched.status_code == status.HTTP_200_OK
    assert patched.data["status"] == "done"

    comment = authenticated_client.post(
        f"/api/delivery/tasks/{task_id}/comments/",
        {"body": "note", "kind": "comment"},
        format="json",
    )
    assert comment.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
def test_overview_when_disabled(authenticated_client, workspace):
    resp = authenticated_client.get("/api/delivery/overview/")
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["agent_ops_enabled"] is False


@pytest.mark.django_db
def test_project_meta(authenticated_client, enable_ops, workspace):
    from projects.models import Project

    project = Project.objects.create(workspace=workspace, name="CryptoGamp ops")
    listing = authenticated_client.get("/api/delivery/projects/")
    assert listing.status_code == status.HTTP_200_OK
    assert any(row["project"] == project.id for row in listing.data)
    assert any(row["project_name"] == "CryptoGamp ops" for row in listing.data)

    resp = authenticated_client.post(
        "/api/delivery/projects/",
        {
            "project": project.id,
            "repo_url": "https://github.com/org/cryptogamp",
            "docs_url": "https://example.com/docs",
        },
        format="json",
    )
    assert resp.status_code == status.HTTP_201_CREATED
    assert resp.data["repo_url"].endswith("cryptogamp")
    assert resp.data["description"] == ""
    assert resp.data["status"] == project.status
