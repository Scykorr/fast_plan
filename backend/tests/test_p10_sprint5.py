"""P10 sprint 5+: PERT finish, adapters, renewals, spawn, cross-deps, 1C SKU."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework import status

from crm.models import Activity, CrmDocument, CrmSku, IntegrationConnector
from process.models import ProcessInstance
from projects.models import CrossProjectDependency, Project, ScheduleActivity


SIMPLE_BPMN = """<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
  id="Defs_1" targetNamespace="http://fastplan.local/bpmn">
  <bpmn:process id="EventProcess" name="Event" isExecutable="true">
    <bpmn:startEvent id="StartEvent_1" name="Start">
      <bpmn:outgoing>Flow_1</bpmn:outgoing>
    </bpmn:startEvent>
    <bpmn:endEvent id="EndEvent_1" name="End">
      <bpmn:incoming>Flow_1</bpmn:incoming>
    </bpmn:endEvent>
    <bpmn:sequenceFlow id="Flow_1" sourceRef="StartEvent_1" targetRef="EndEvent_1" />
  </bpmn:process>
</bpmn:definitions>
"""


@pytest.mark.django_db
def test_pert_finish_percentiles(authenticated_client, workspace, user):
    project = Project.objects.create(
        workspace=workspace,
        name="PERT",
        manager=user,
        start_date=timezone.localdate(),
    )
    root = project.wbs_nodes.get(code="1")
    created = authenticated_client.post(
        f"/api/projects/{project.id}/wbs/",
        {
            "title": "Build",
            "parent_id": root.id,
            "node_type": "work_package",
        },
        format="json",
    )
    assert created.status_code == status.HTTP_201_CREATED
    from projects.models import WBSNode

    node = WBSNode.objects.get(project=project, title="Build")
    activity = ScheduleActivity.objects.get(wbs_node=node)
    activity.duration_days = 10
    activity.save(update_fields=["duration_days"])
    resp = authenticated_client.get(f"/api/projects/{project.id}/pert/")
    assert resp.status_code == status.HTTP_200_OK
    finish = resp.data["finish"]
    assert "p10_days" in finish and "p50_days" in finish and "p90_days" in finish
    assert finish["p10_days"] <= finish["p50_days"] <= finish["p90_days"]
    assert finish["p10_date"]
    assert finish["p90_date"]


@pytest.mark.django_db
def test_process_adapters_catalog(authenticated_client, workspace):
    resp = authenticated_client.get("/api/process/adapters/")
    assert resp.status_code == status.HTTP_200_OK
    ops = {a["operation"] for a in resp.data["adapters"]}
    assert "create_wbs_note" in ops
    assert "create_activity" in ops
    types = {e["type"] for e in resp.data["executable_elements"]}
    assert "inclusiveGateway" in types
    assert "subProcess" in types


@pytest.mark.django_db
def test_contract_renewals_arr(authenticated_client, workspace, user):
    today = timezone.localdate()
    CrmDocument.objects.create(
        workspace=workspace,
        doc_type=CrmDocument.DocType.CONTRACT,
        title="Support",
        status=CrmDocument.Status.ACCEPTED,
        amount=Decimal("120000"),
        arr_annual=Decimal("120000"),
        renewal_date=today + timedelta(days=30),
        term_months=12,
        created_by=user,
    )
    resp = authenticated_client.get("/api/crm/renewals/?within_days=90")
    assert resp.status_code == status.HTTP_200_OK
    assert Decimal(resp.data["arr_total"]) == Decimal("120000.00")
    assert len(resp.data["upcoming"]) == 1
    assert resp.data["upcoming"][0]["days_until"] == 30


@pytest.mark.django_db
def test_activity_spawn_wbs(authenticated_client, workspace, user):
    from crm.models import Organization

    org = Organization.objects.create(workspace=workspace, name="Spawn Org")
    project = Project.objects.create(
        workspace=workspace, name="Spawn target", manager=user
    )
    activity = Activity.objects.create(
        workspace=workspace,
        kind=Activity.Kind.NOTE,
        subject="Follow-up call",
        body="Details",
        organization=org,
        occurred_at=timezone.now(),
        created_by=user,
    )
    resp = authenticated_client.post(
        f"/api/crm/activities/{activity.id}/spawn/",
        {"mode": "wbs", "project_id": project.id},
        format="json",
    )
    assert resp.status_code == status.HTTP_201_CREATED
    assert resp.data["mode"] == "wbs"
    assert resp.data["wbs_node_id"]
    assert project.wbs_nodes.filter(title="Follow-up call").exists()


@pytest.mark.django_db
def test_activity_created_starts_process_by_category(
    authenticated_client, workspace, user
):
    from crm.models import Organization

    org = Organization.objects.create(workspace=workspace, name="Event Org")
    create = authenticated_client.post(
        "/api/process/definitions/",
        {
            "key": "on-activity",
            "name": "On activity",
            "bpmn_xml": SIMPLE_BPMN,
            "process_id": "EventProcess",
            "category": "activity.created",
        },
        format="json",
    )
    assert create.status_code == status.HTTP_201_CREATED
    authenticated_client.post(
        f"/api/process/definitions/{create.data['id']}/publish/",
        {},
        format="json",
    )
    before = ProcessInstance.objects.filter(workspace=workspace).count()
    act = authenticated_client.post(
        "/api/crm/activities/",
        {
            "kind": "note",
            "subject": "Kickoff",
            "body": "",
            "organization_id": org.id,
        },
        format="json",
    )
    assert act.status_code == status.HTTP_201_CREATED
    assert ProcessInstance.objects.filter(workspace=workspace).count() == before + 1


@pytest.mark.django_db
def test_cross_project_dependency(authenticated_client, workspace, user):
    p1 = Project.objects.create(workspace=workspace, name="A", manager=user)
    p2 = Project.objects.create(workspace=workspace, name="B", manager=user)
    root1 = p1.wbs_nodes.get(code="1")
    root2 = p2.wbs_nodes.get(code="1")
    w1 = authenticated_client.post(
        f"/api/projects/{p1.id}/wbs/",
        {"title": "A1", "parent_id": root1.id, "node_type": "work_package"},
        format="json",
    )
    w2 = authenticated_client.post(
        f"/api/projects/{p2.id}/wbs/",
        {"title": "B1", "parent_id": root2.id, "node_type": "work_package"},
        format="json",
    )
    assert w1.status_code == status.HTTP_201_CREATED
    assert w2.status_code == status.HTTP_201_CREATED
    from projects.models import WBSNode

    n1 = WBSNode.objects.get(project=p1, title="A1")
    n2 = WBSNode.objects.get(project=p2, title="B1")
    a1 = ScheduleActivity.objects.get(wbs_node=n1)
    a2 = ScheduleActivity.objects.get(wbs_node=n2)
    create = authenticated_client.post(
        "/api/workspace/cross-dependencies/",
        {
            "predecessor_id": a1.id,
            "successor_id": a2.id,
            "dependency_type": "FS",
            "lag_days": 2,
            "note": "handoff",
        },
        format="json",
    )
    assert create.status_code == status.HTTP_201_CREATED
    assert CrossProjectDependency.objects.filter(
        workspace=workspace, predecessor=a1, successor=a2
    ).exists()
    listed = authenticated_client.get("/api/workspace/cross-dependencies/")
    assert listed.status_code == status.HTTP_200_OK
    assert any(row["id"] == create.data["id"] for row in listed.data)


@pytest.mark.django_db
def test_onec_sku_sync_from_pending(authenticated_client, workspace, user):
    connector = IntegrationConnector.objects.create(
        workspace=workspace,
        provider=IntegrationConnector.Provider.ONEC,
        name="1C lite",
        config={
            "pending_skus": [
                {
                    "code": "1C-100",
                    "name": "License",
                    "unit_price": "999.50",
                    "id": "ref-100",
                }
            ]
        },
    )
    sync = authenticated_client.post(
        f"/api/crm/connectors/{connector.id}/sync/",
        {},
        format="json",
    )
    assert sync.status_code == status.HTTP_200_OK
    sku = CrmSku.objects.get(workspace=workspace, code="1C-100")
    assert sku.name == "License"
    assert sku.external_ref == "ref-100"
    assert Decimal(str(sku.unit_price)) == Decimal("999.50")
