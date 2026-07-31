"""P10 sprint 1: deal→project handoff + process ops."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework import status

from crm.models import Deal, Organization
from crm.services import ensure_default_pipeline
from process.models import ProcessDefinition, ProcessDeployment, ProcessInstance, UserTask
from process.ops import build_process_ops
from projects.models import Project, ProjectTemplate


@pytest.mark.django_db
def test_create_project_from_deal_with_template(authenticated_client, workspace, user):
    pipeline = ensure_default_pipeline(workspace)
    won = pipeline.stages.filter(is_won=True).first()
    assert won is not None
    org = Organization.objects.create(workspace=workspace, name="Acme")
    deal = Deal.objects.create(
        workspace=workspace,
        pipeline=pipeline,
        stage=won,
        title="Won deal delivery",
        amount=Decimal("1000"),
        organization=org,
        owner=user,
    )
    template = ProjectTemplate.objects.create(
        workspace=workspace,
        name="Delivery tpl",
        description="",
        structure={
            "columns": ["Backlog", "Done"],
            "wbs": [
                {
                    "code": "1",
                    "parent_code": None,
                    "title": "{{ project_name }}",
                    "description": "",
                    "node_type": "project",
                    "position": 0,
                }
            ],
        },
        created_by=user,
    )

    resp = authenticated_client.post(
        f"/api/crm/deals/{deal.id}/create-project/",
        {"template_id": template.id},
        format="json",
    )
    assert resp.status_code == status.HTTP_201_CREATED
    assert resp.data["deal"]["project"] == resp.data["project"]["id"]
    assert resp.data["project"]["name"] == "Won deal delivery"
    assert resp.data["project"]["client_organization_id"] == org.id

    deal.refresh_from_db()
    assert deal.project_id == resp.data["project"]["id"]
    assert Project.objects.filter(pk=deal.project_id).exists()

    again = authenticated_client.post(
        f"/api/crm/deals/{deal.id}/create-project/",
        {},
        format="json",
    )
    assert again.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_process_ops_lists_stuck_aging_and_sla(authenticated_client, workspace, user):
    definition = ProcessDefinition.objects.create(
        workspace=workspace,
        key="ops-demo",
        name="Ops demo",
        bpmn_xml="<bpmn/>",
        process_id="OpsDemo",
        created_by=user,
    )
    deployment = ProcessDeployment.objects.create(
        definition=definition,
        workspace=workspace,
        bpmn_xml="<bpmn/>",
        version=1,
        process_id="OpsDemo",
        deployed_by=user,
    )
    old = timezone.now() - timedelta(hours=100)
    stuck = ProcessInstance.objects.create(
        workspace=workspace,
        deployment=deployment,
        status=ProcessInstance.Status.ACTIVE,
        started_at=old,
    )
    ProcessInstance.objects.filter(pk=stuck.pk).update(started_at=old)

    err = ProcessInstance.objects.create(
        workspace=workspace,
        deployment=deployment,
        status=ProcessInstance.Status.ERROR,
        error_message="boom",
    )

    aging_inst = ProcessInstance.objects.create(
        workspace=workspace,
        deployment=deployment,
        status=ProcessInstance.Status.ACTIVE,
    )
    aging_task = UserTask.objects.create(
        workspace=workspace,
        instance=aging_inst,
        spiff_task_id="t1",
        name="Old task",
        status=UserTask.Status.OPEN,
    )
    UserTask.objects.filter(pk=aging_task.pk).update(
        created_at=timezone.now() - timedelta(hours=60)
    )

    sla_task = UserTask.objects.create(
        workspace=workspace,
        instance=aging_inst,
        spiff_task_id="t2",
        name="Overdue task",
        status=UserTask.Status.OPEN,
        due_at=timezone.now() - timedelta(hours=2),
    )

    payload = build_process_ops(workspace, stuck_hours=72, aging_hours=48)
    stuck_ids = {row["id"] for row in payload["stuck_instances"]}
    assert stuck.id in stuck_ids
    assert err.id in stuck_ids
    aging_ids = {row["id"] for row in payload["aging_tasks"]}
    assert aging_task.id in aging_ids
    sla_ids = {row["id"] for row in payload["sla_breaches"]}
    assert sla_task.id in sla_ids

    api = authenticated_client.get("/api/process/ops/")
    assert api.status_code == status.HTTP_200_OK
    assert "stuck_instances" in api.data
    assert api.data["counts"]["sla_breaches"] >= 1
