"""P6e CRM BPM-lite automation + deal reorder tests."""

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework import status

from crm.automation import apply_deal_move, process_deferred_automations
from crm.models import AutomationDeferred, AutomationRule, Deal, DealTask, Lead
from crm.services import ensure_default_pipeline


@pytest.mark.django_db
def test_automation_templates_and_lead_created(authenticated_client, workspace, user):
    templates = authenticated_client.get("/api/crm/automations/templates/")
    assert templates.status_code == status.HTTP_200_OK
    keys = {row["key"] for row in templates.data}
    assert "form_lead" in keys
    assert "follow_up_2d" in keys

    applied = authenticated_client.post(
        "/api/crm/automations/templates/apply/",
        {"template_key": "form_lead"},
        format="json",
    )
    assert applied.status_code == status.HTTP_201_CREATED
    assert applied.data["trigger"] == "lead.created"

    lead = authenticated_client.post(
        "/api/crm/leads/",
        {
            "full_name": "Form Lead",
            "email": "form@ex.test",
            "source": "form",
            "company_name": "FormCo",
        },
        format="json",
    )
    assert lead.status_code == status.HTTP_201_CREATED
    # round-robin assign from automation
    refreshed = authenticated_client.get(f"/api/crm/leads/{lead.data['id']}/")
    assert refreshed.data["assigned_to"] == user.id

    runs = authenticated_client.get("/api/crm/automations/runs/")
    assert runs.status_code == status.HTTP_200_OK
    assert any(r["trigger"] == "lead.created" for r in runs.data)


@pytest.mark.django_db
def test_follow_up_template_creates_deal_task(authenticated_client, workspace, user):
    authenticated_client.post(
        "/api/crm/automations/templates/apply/",
        {"template_key": "follow_up_2d"},
        format="json",
    )
    deal = authenticated_client.post(
        "/api/crm/deals/",
        {"title": "Auto deal", "amount": "1000"},
        format="json",
    )
    assert deal.status_code == status.HTTP_201_CREATED
    tasks = DealTask.objects.filter(deal_id=deal.data["id"])
    assert tasks.count() == 1
    assert tasks.first().title == "Follow-up по сделке"


@pytest.mark.django_db
def test_delay_action_deferred(authenticated_client, workspace, user):
    AutomationRule.objects.create(
        workspace=workspace,
        name="Delay assign",
        trigger=AutomationRule.Trigger.LEAD_CREATED,
        conditions=[],
        actions=[
            {"type": "delay", "minutes": 0},
            {"type": "assign_round_robin"},
        ],
        is_active=True,
    )
    lead = Lead.objects.create(
        workspace=workspace, full_name="Delayed", email="d@ex.test", source="ads"
    )
    from crm.automation import build_lead_context, run_automations

    run_automations(
        workspace,
        AutomationRule.Trigger.LEAD_CREATED,
        build_lead_context(lead, trigger=AutomationRule.Trigger.LEAD_CREATED),
    )
    assert AutomationDeferred.objects.filter(processed_at__isnull=True).exists()
    deferred = AutomationDeferred.objects.first()
    deferred.run_at = timezone.now() - timedelta(minutes=1)
    deferred.save(update_fields=["run_at"])
    processed = process_deferred_automations()
    assert processed >= 1
    lead.refresh_from_db()
    assert lead.assigned_to_id == user.id


@pytest.mark.django_db
def test_deal_move_reindexes_positions(authenticated_client, workspace, user):
    pipeline = ensure_default_pipeline(workspace)
    stage = pipeline.stages.order_by("position").first()
    other = pipeline.stages.order_by("position")[1]
    d1 = Deal.objects.create(
        workspace=workspace,
        pipeline=pipeline,
        stage=stage,
        title="A",
        position=0,
        owner=user,
    )
    d2 = Deal.objects.create(
        workspace=workspace,
        pipeline=pipeline,
        stage=stage,
        title="B",
        position=1,
        owner=user,
    )
    d3 = Deal.objects.create(
        workspace=workspace,
        pipeline=pipeline,
        stage=stage,
        title="C",
        position=2,
        owner=user,
    )

    # Move C to top of same column
    moved = authenticated_client.post(
        f"/api/crm/deals/{d3.id}/move/",
        {"stage_id": stage.id, "position": 0},
        format="json",
    )
    assert moved.status_code == status.HTTP_200_OK
    assert moved.data["position"] == 0
    positions = {
        d.id: d.position
        for d in Deal.objects.filter(stage=stage).order_by("position")
    }
    assert positions[d3.id] == 0
    assert sorted(positions.values()) == [0, 1, 2]

    # Move B to other stage at position 0 and ensure old column reindexed
    authenticated_client.post(
        f"/api/crm/deals/{d2.id}/move/",
        {"stage_id": other.id, "position": 0},
        format="json",
    )
    old_positions = list(
        Deal.objects.filter(stage=stage).order_by("position").values_list("position", flat=True)
    )
    assert old_positions == list(range(len(old_positions)))
    assert Deal.objects.get(pk=d2.id).stage_id == other.id
    assert Deal.objects.get(pk=d2.id).position == 0

    # helper sanity
    apply_deal_move(d1, stage, position=1)
    d1.refresh_from_db()
    assert d1.position == 1
