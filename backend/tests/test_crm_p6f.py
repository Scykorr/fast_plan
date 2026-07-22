"""P6f AI CRM + schedule.daily stale deals."""

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework import status

from crm.automation import run_schedule_daily_automations
from crm.models import AutomationRule, Deal, DealTask
from crm.services import ensure_default_pipeline


@pytest.mark.django_db
def test_ai_insights_and_drafts(authenticated_client, workspace, user):
    pipeline = ensure_default_pipeline(workspace)
    stage = pipeline.stages.exclude(is_won=True).exclude(is_lost=True).first()
    deal = Deal.objects.create(
        workspace=workspace,
        pipeline=pipeline,
        stage=stage,
        title="At risk",
        amount=5000,
        probability=20,
        close_date=timezone.localdate() - timedelta(days=1),
        owner=user,
    )
    Deal.objects.filter(pk=deal.pk).update(
        updated_at=timezone.now() - timedelta(days=20)
    )

    insights = authenticated_client.get("/api/crm/ai/insights/?stale_days=14")
    assert insights.status_code == status.HTTP_200_OK
    assert "summary" in insights.data
    assert "at_risk_deals" in insights.data
    assert any(row["id"] == deal.id for row in insights.data["at_risk_deals"])

    email = authenticated_client.post(
        "/api/crm/ai/draft-email/",
        {"deal_id": deal.id, "prompt": "коротко"},
        format="json",
    )
    assert email.status_code == status.HTTP_200_OK
    assert email.data["subject"]
    assert email.data["body"]

    kp = authenticated_client.post(
        "/api/crm/ai/draft-kp/",
        {"deal_id": deal.id},
        format="json",
    )
    assert kp.status_code == status.HTTP_200_OK
    assert kp.data["markdown"]

    summary = authenticated_client.post(
        "/api/crm/ai/activity-summary/",
        {"deal_id": deal.id},
        format="json",
    )
    assert summary.status_code == status.HTTP_200_OK
    assert summary.data["summary"]

    suggest = authenticated_client.post(
        "/api/crm/ai/suggest-tasks/",
        {"deal_id": deal.id, "apply": True},
        format="json",
    )
    assert suggest.status_code == status.HTTP_200_OK
    assert suggest.data["tasks"]
    assert suggest.data["created"]
    assert DealTask.objects.filter(deal=deal).count() >= 1


@pytest.mark.django_db
def test_schedule_daily_stale_deal_template(authenticated_client, workspace, user):
    applied = authenticated_client.post(
        "/api/crm/automations/templates/apply/",
        {"template_key": "stale_deal_daily"},
        format="json",
    )
    assert applied.status_code == status.HTTP_201_CREATED
    assert applied.data["trigger"] == "schedule.daily"

    templates = authenticated_client.get("/api/crm/automations/templates/")
    keys = {row["key"] for row in templates.data}
    assert "stale_deal_daily" in keys

    pipeline = ensure_default_pipeline(workspace)
    stage = pipeline.stages.exclude(is_won=True).exclude(is_lost=True).first()
    deal = Deal.objects.create(
        workspace=workspace,
        pipeline=pipeline,
        stage=stage,
        title="Stale open",
        amount=1000,
        probability=50,
        owner=user,
    )
    Deal.objects.filter(pk=deal.pk).update(
        updated_at=timezone.now() - timedelta(days=20),
        created_at=timezone.now() - timedelta(days=30),
    )

    fresh = Deal.objects.create(
        workspace=workspace,
        pipeline=pipeline,
        stage=stage,
        title="Fresh",
        amount=100,
        probability=50,
        owner=user,
    )

    stats = run_schedule_daily_automations(workspace=workspace)
    assert stats["runs"] >= 1
    assert DealTask.objects.filter(
        deal=deal, title="Stale deal — вернуть в контакт"
    ).exists()
    assert not DealTask.objects.filter(deal=fresh).exists()

    # Second run skips duplicate open task
    before = DealTask.objects.filter(deal=deal).count()
    run_schedule_daily_automations(workspace=workspace)
    assert DealTask.objects.filter(deal=deal).count() == before


@pytest.mark.django_db
def test_automation_rule_visual_fields_roundtrip(authenticated_client, workspace):
    created = authenticated_client.post(
        "/api/crm/automations/",
        {
            "name": "Daily stale custom",
            "trigger": "schedule.daily",
            "conditions": [{"field": "days_since_touch", "op": "gte", "value": 10}],
            "actions": [
                {
                    "type": "create_deal_task",
                    "title": "Ping",
                    "due_in_days": 1,
                    "skip_if_open": True,
                }
            ],
        },
        format="json",
    )
    assert created.status_code == status.HTTP_201_CREATED
    assert created.data["trigger"] == AutomationRule.Trigger.SCHEDULE_DAILY
    assert created.data["conditions"][0]["field"] == "days_since_touch"
