"""P6c CRM deals / pipeline API tests."""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from rest_framework import status

from crm.models import Deal, Organization
from crm.services import ensure_default_pipeline
from finance.models import Transaction
from notifications.models import Notification
from notifications.services import send_deal_task_reminders


@pytest.mark.django_db
def test_pipeline_deal_move_and_forecast(authenticated_client, workspace, user):
    pipeline = authenticated_client.get("/api/crm/pipeline/")
    assert pipeline.status_code == status.HTTP_200_OK
    stages = pipeline.data["stages"]
    assert len(stages) >= 4
    first = stages[0]
    proposal = next(s for s in stages if s["name"] == "Предложение")
    won = next(s for s in stages if s["is_won"])

    org = Organization.objects.create(workspace=workspace, name="Buyer Co")
    created = authenticated_client.post(
        "/api/crm/deals/",
        {
            "title": "Enterprise license",
            "amount": "100000.00",
            "organization_id": org.id,
            "close_date": (date.today() + timedelta(days=30)).isoformat(),
        },
        format="json",
    )
    assert created.status_code == status.HTTP_201_CREATED
    assert created.data["stage"] == first["id"]
    assert created.data["probability"] == first["default_probability"]
    assert created.data["organization_name"] == "Buyer Co"
    deal_id = created.data["id"]

    moved = authenticated_client.post(
        f"/api/crm/deals/{deal_id}/move/",
        {"stage_id": proposal["id"]},
        format="json",
    )
    assert moved.status_code == status.HTTP_200_OK
    assert moved.data["stage"] == proposal["id"]
    assert moved.data["probability"] == proposal["default_probability"]

    forecast = authenticated_client.get("/api/crm/deals/forecast/")
    assert forecast.status_code == status.HTTP_200_OK
    assert forecast.data["open_count"] == 1
    expected = float(Decimal("100000") * proposal["default_probability"] / 100)
    assert forecast.data["forecast_amount"] == expected

    authenticated_client.post(
        f"/api/crm/deals/{deal_id}/move/",
        {"stage_id": won["id"]},
        format="json",
    )
    forecast2 = authenticated_client.get("/api/crm/deals/forecast/")
    assert forecast2.data["open_count"] == 0
    assert forecast2.data["won_count"] == 1
    assert forecast2.data["won_amount"] == 100000.0


@pytest.mark.django_db
def test_deal_tasks_and_reminders(authenticated_client, workspace, user):
    ensure_default_pipeline(workspace)
    deal = authenticated_client.post(
        "/api/crm/deals/",
        {"title": "Pilot", "amount": "5000"},
        format="json",
    )
    deal_id = deal.data["id"]
    due = date.today()
    task = authenticated_client.post(
        f"/api/crm/deals/{deal_id}/tasks/",
        {
            "title": "Send proposal",
            "due_date": due.isoformat(),
            "assignee_id": user.id,
            "remind_before_days": 0,
        },
        format="json",
    )
    assert task.status_code == status.HTTP_201_CREATED

    listed = authenticated_client.get(f"/api/crm/deals/{deal_id}/tasks/")
    assert listed.status_code == status.HTTP_200_OK
    assert listed.data[0]["title"] == "Send proposal"

    created, items = send_deal_task_reminders(today=due)
    assert created >= 1
    assert Notification.objects.filter(
        notification_type=Notification.NotificationType.DEAL_TASK,
        user=user,
    ).exists()
    assert items


@pytest.mark.django_db
def test_deal_project_link_and_finance_counterparty(
    authenticated_client, workspace, user
):
    from projects.models import Project

    pipeline = ensure_default_pipeline(workspace)
    org = Organization.objects.create(workspace=workspace, name="Client Org")
    project = Project.objects.create(
        workspace=workspace, name="Delivery", manager=user
    )
    deal = Deal.objects.create(
        workspace=workspace,
        pipeline=pipeline,
        stage=pipeline.stages.first(),
        title="Linked deal",
        amount=Decimal("25000"),
        probability=50,
        organization=org,
        project=project,
        owner=user,
    )

    patched = authenticated_client.patch(
        f"/api/crm/deals/{deal.id}/",
        {"project_id": project.id, "organization_id": org.id},
        format="json",
    )
    assert patched.status_code == status.HTTP_200_OK
    assert patched.data["project"] == project.id
    assert patched.data["organization"] == org.id

    tx = authenticated_client.post(
        "/api/finance/transactions/",
        {
            "title": "Prepayment",
            "amount": "10000.00",
            "transaction_type": "income",
            "transaction_date": date.today().isoformat(),
            "organization_id": org.id,
            "deal_id": deal.id,
            "project_id": project.id,
        },
        format="json",
    )
    assert tx.status_code == status.HTTP_201_CREATED
    assert tx.data["organization_id"] == org.id
    assert tx.data["deal_id"] == deal.id
    assert Transaction.objects.filter(deal=deal, organization=org).exists()
