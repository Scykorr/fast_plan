from datetime import date, timedelta

import pytest

from crm.models import Deal, DealTask, Lead, LeadTask, PipelineStage
from crm.services import ensure_default_pipeline


@pytest.fixture
def deal(workspace, user):
    pipeline = ensure_default_pipeline(workspace)
    stage = pipeline.stages.first()
    return Deal.objects.create(
        workspace=workspace,
        pipeline=pipeline,
        stage=stage,
        title="Acme deal",
        owner=user,
        amount=1000,
        probability=50,
    )


@pytest.fixture
def lead(workspace, user):
    return Lead.objects.create(
        workspace=workspace,
        full_name="Ivan Lead",
        email="ivan@example.com",
        assigned_to=user,
    )


def test_deal_task_priority_checklist_and_board(authenticated_client, deal):
    created = authenticated_client.post(
        f"/api/crm/deals/{deal.id}/tasks/",
        {
            "title": "Call",
            "priority": "high",
            "repeat": "weekly",
            "checklist": [{"text": "Prepare script"}, {"text": "Dial"}],
            "due_date": str(date.today()),
        },
        format="json",
    )
    assert created.status_code == 201
    assert created.data["priority"] == "high"
    assert created.data["board_status"] == "todo"
    assert created.data["checklist_total"] == 2
    task_id = created.data["id"]

    moved = authenticated_client.patch(
        f"/api/crm/tasks/board/deal/{task_id}/",
        {"board_status": "doing"},
        format="json",
    )
    assert moved.status_code == 200
    assert moved.data["board_status"] == "doing"

    board = authenticated_client.get("/api/crm/tasks/board/?include_done=1")
    assert board.status_code == 200
    assert any(row["id"] == task_id and row["kind"] == "deal" for row in board.data["results"])


def test_repeat_spawns_next_on_complete(authenticated_client, deal):
    due = date.today()
    created = authenticated_client.post(
        f"/api/crm/deals/{deal.id}/tasks/",
        {
            "title": "Weekly sync",
            "repeat": "weekly",
            "due_date": str(due),
        },
        format="json",
    )
    assert created.status_code == 201
    task_id = created.data["id"]

    done = authenticated_client.patch(
        f"/api/crm/deals/{deal.id}/tasks/{task_id}/",
        {"is_done": True},
        format="json",
    )
    assert done.status_code == 200
    assert done.data["is_done"] is True
    assert done.data["board_status"] == "done"

    open_tasks = DealTask.objects.filter(deal=deal, is_done=False, title="Weekly sync")
    assert open_tasks.count() == 1
    assert open_tasks.first().due_date == due + timedelta(weeks=1)


def test_lead_task_and_unified_board(authenticated_client, lead, deal):
    lead_task = authenticated_client.post(
        f"/api/crm/leads/{lead.id}/tasks/",
        {"title": "Qualify", "priority": "urgent"},
        format="json",
    )
    assert lead_task.status_code == 201
    deal_task = authenticated_client.post(
        f"/api/crm/deals/{deal.id}/tasks/",
        {"title": "Send quote"},
        format="json",
    )
    assert deal_task.status_code == 201

    board = authenticated_client.get("/api/crm/tasks/board/")
    assert board.status_code == 200
    kinds = {row["kind"] for row in board.data["results"]}
    assert kinds == {"deal", "lead"}
    assert LeadTask.objects.filter(lead=lead).count() == 1
