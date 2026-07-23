"""P8 Process API and engine tests."""

import pytest
from rest_framework import status

from process.dmn import evaluate_decision
from process.engine import parse_process_id, start_instance
from process.migration_tools import automation_rule_to_bpmn
from process.models import (
    CaseDefinition,
    CaseInstance,
    DecisionDefinition,
    ProcessDefinition,
    ProcessInstance,
    UserTask,
)
from process.services import publish_definition

SIMPLE_BPMN = """<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
  id="Defs_1" targetNamespace="http://fastplan.local/bpmn">
  <bpmn:process id="SimpleProcess" name="Simple" isExecutable="true">
    <bpmn:startEvent id="StartEvent_1" name="Start">
      <bpmn:outgoing>Flow_1</bpmn:outgoing>
    </bpmn:startEvent>
    <bpmn:userTask id="Activity_Approve" name="Approve">
      <bpmn:incoming>Flow_1</bpmn:incoming>
      <bpmn:outgoing>Flow_2</bpmn:outgoing>
    </bpmn:userTask>
    <bpmn:serviceTask id="Activity_Notify" name="notify">
      <bpmn:incoming>Flow_2</bpmn:incoming>
      <bpmn:outgoing>Flow_3</bpmn:outgoing>
    </bpmn:serviceTask>
    <bpmn:endEvent id="EndEvent_1" name="End">
      <bpmn:incoming>Flow_3</bpmn:incoming>
    </bpmn:endEvent>
    <bpmn:sequenceFlow id="Flow_1" sourceRef="StartEvent_1" targetRef="Activity_Approve" />
    <bpmn:sequenceFlow id="Flow_2" sourceRef="Activity_Approve" targetRef="Activity_Notify" />
    <bpmn:sequenceFlow id="Flow_3" sourceRef="Activity_Notify" targetRef="EndEvent_1" />
  </bpmn:process>
</bpmn:definitions>
"""


def test_parse_process_id_spike():
    assert parse_process_id(SIMPLE_BPMN) == "SimpleProcess"


@pytest.mark.django_db
def test_publish_start_complete_user_task(authenticated_client, workspace, user):
    create = authenticated_client.post(
        "/api/process/definitions/",
        {
            "key": "simple",
            "name": "Simple process",
            "bpmn_xml": SIMPLE_BPMN,
            "process_id": "SimpleProcess",
        },
        format="json",
    )
    assert create.status_code == status.HTTP_201_CREATED
    pk = create.data["id"]

    pub = authenticated_client.post(f"/api/process/definitions/{pk}/publish/", {}, format="json")
    assert pub.status_code == status.HTTP_200_OK

    start = authenticated_client.post(
        f"/api/process/definitions/{pk}/start/",
        {"data": {"title": "hello"}},
        format="json",
    )
    assert start.status_code == status.HTTP_201_CREATED
    instance_id = start.data["id"]
    assert start.data["status"] == ProcessInstance.Status.ACTIVE

    tasks = authenticated_client.get("/api/process/tasks/?status=open")
    assert tasks.status_code == status.HTTP_200_OK
    assert len(tasks.data) >= 1
    task_id = tasks.data[0]["id"]

    done = authenticated_client.post(
        f"/api/process/tasks/{task_id}/complete/",
        {"form_data": {"approved": True}, "note": "ok"},
        format="json",
    )
    assert done.status_code == status.HTTP_200_OK
    assert done.data["instance"]["status"] == ProcessInstance.Status.COMPLETED


@pytest.mark.django_db
def test_dmn_lite_evaluate(workspace):
    DecisionDefinition.objects.create(
        workspace=workspace,
        key="route",
        name="Route",
        decision_id="decision_1",
        dmn_xml='<!--fp-rules\n[{"when": {"score_gte": 70}, "then": {"route": "a"}}, {"when": {}, "then": {"route": "b"}}]\n-->',
    )
    result = evaluate_decision(workspace=workspace, decision_key="route", inputs={"score": 90})
    assert result.get("route") == "a"


@pytest.mark.django_db
def test_case_instance_flow(authenticated_client, workspace):
    definition = CaseDefinition.objects.create(
        workspace=workspace,
        key="support",
        name="Support case",
        plan_items=[
            {"id": "triage", "name": "Triage"},
            {"id": "resolve", "name": "Resolve", "discretionary": True},
        ],
    )
    create = authenticated_client.post(
        "/api/process/cases/",
        {"definition_id": definition.id, "title": "Ticket 1"},
        format="json",
    )
    assert create.status_code == status.HTTP_201_CREATED
    case_id = create.data["id"]
    complete = authenticated_client.post(
        f"/api/process/cases/{case_id}/complete-item/",
        {"item_id": "triage"},
        format="json",
    )
    assert complete.status_code == status.HTTP_200_OK
    assert "triage" in complete.data["completed_items"]


@pytest.mark.django_db
def test_pack_list_and_import(authenticated_client):
    listed = authenticated_client.get("/api/process/packs/")
    assert listed.status_code == status.HTTP_200_OK
    assert len(listed.data) >= 3
    pack_id = listed.data[0]["id"]
    imported = authenticated_client.post(
        "/api/process/packs/import/",
        {"pack_id": pack_id},
        format="json",
    )
    assert imported.status_code in (status.HTTP_200_OK, status.HTTP_201_CREATED)
    assert imported.data["definition"]["key"]


@pytest.mark.django_db
def test_metrics_and_migrate(authenticated_client, workspace, user):
    from crm.models import AutomationRule

    metrics = authenticated_client.get("/api/process/metrics/")
    assert metrics.status_code == status.HTTP_200_OK
    assert "instance_count" in metrics.data

    rule = AutomationRule.objects.create(
        workspace=workspace,
        name="Follow up",
        trigger=AutomationRule.Trigger.DEAL_CREATED,
        conditions=[],
        actions=[{"type": "create_deal_task", "title": "Call"}],
        is_active=True,
    )
    migrated = authenticated_client.post(
        "/api/process/migrate-automation/",
        {"automation_rule_id": rule.id},
        format="json",
    )
    assert migrated.status_code == status.HTTP_201_CREATED
    assert "migrated" in migrated.data["name"].lower()
    payload = automation_rule_to_bpmn(rule)
    assert "bpmn:process" in payload["bpmn_xml"]


@pytest.mark.django_db
def test_export_definition(authenticated_client, workspace, user):
    definition = ProcessDefinition.objects.create(
        workspace=workspace,
        key="exp",
        name="Export me",
        bpmn_xml=SIMPLE_BPMN,
        process_id="SimpleProcess",
        created_by=user,
    )
    response = authenticated_client.get(f"/api/process/definitions/{definition.id}/export/")
    assert response.status_code == status.HTTP_200_OK
    assert response.data["bpmn_xml"].startswith("<?xml")
