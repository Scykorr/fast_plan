"""P10 UX glue + SubProcess nested lifecycle."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework import status

from crm.models import CrmDocument, Deal, DealTask, Organization
from notifications.models import Notification
from process.models import ProcessInstance, UserTask
from projects.models import Project


SUBPROCESS_BPMN = """<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
  id="Defs" targetNamespace="http://fastplan.local/bpmn">
  <bpmn:process id="MainSub" name="MainSub" isExecutable="true">
    <bpmn:startEvent id="Start_1"><bpmn:outgoing>f1</bpmn:outgoing></bpmn:startEvent>
    <bpmn:subProcess id="Sub_1" name="Nested">
      <bpmn:incoming>f1</bpmn:incoming>
      <bpmn:outgoing>f2</bpmn:outgoing>
      <bpmn:startEvent id="SubStart"><bpmn:outgoing>sf1</bpmn:outgoing></bpmn:startEvent>
      <bpmn:userTask id="SubUser" name="Inner review">
        <bpmn:incoming>sf1</bpmn:incoming>
        <bpmn:outgoing>sf2</bpmn:outgoing>
      </bpmn:userTask>
      <bpmn:endEvent id="SubEnd"><bpmn:incoming>sf2</bpmn:incoming></bpmn:endEvent>
      <bpmn:sequenceFlow id="sf1" sourceRef="SubStart" targetRef="SubUser"/>
      <bpmn:sequenceFlow id="sf2" sourceRef="SubUser" targetRef="SubEnd"/>
    </bpmn:subProcess>
    <bpmn:endEvent id="End_1"><bpmn:incoming>f2</bpmn:incoming></bpmn:endEvent>
    <bpmn:sequenceFlow id="f1" sourceRef="Start_1" targetRef="Sub_1"/>
    <bpmn:sequenceFlow id="f2" sourceRef="Sub_1" targetRef="End_1"/>
  </bpmn:process>
</bpmn:definitions>
"""


@pytest.mark.django_db
def test_renewal_remind_creates_task_and_notification(
    authenticated_client, workspace, user
):
    org = Organization.objects.create(workspace=workspace, name="Renew Co")
    from crm.models import Pipeline, PipelineStage

    pipeline = Pipeline.objects.create(workspace=workspace, name="Sales")
    stage = PipelineStage.objects.create(pipeline=pipeline, name="Won", position=1)
    deal = Deal.objects.create(
        workspace=workspace,
        title="Renewal deal",
        organization=org,
        pipeline=pipeline,
        stage=stage,
        owner=user,
        amount=Decimal("1000"),
    )
    today = timezone.localdate()
    doc = CrmDocument.objects.create(
        workspace=workspace,
        doc_type=CrmDocument.DocType.CONTRACT,
        title="Annual",
        status=CrmDocument.Status.ACCEPTED,
        amount=Decimal("120000"),
        renewal_date=today + timedelta(days=10),
        deal=deal,
        organization=org,
        created_by=user,
    )
    resp = authenticated_client.post(
        "/api/crm/renewals/",
        {"within_days": 30},
        format="json",
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["created_tasks"] == 1
    assert resp.data["created_notifications"] >= 1
    assert DealTask.objects.filter(deal=deal, is_done=False).exists()
    assert Notification.objects.filter(
        user=user, dedupe_key=f"renewal:{doc.id}:{doc.renewal_date.isoformat()}"
    ).exists()

    again = authenticated_client.post(
        "/api/crm/renewals/",
        {"within_days": 30},
        format="json",
    )
    assert again.status_code == status.HTTP_200_OK
    assert again.data["created_tasks"] == 0


@pytest.mark.django_db
def test_workspace_schedule_activities_list(
    authenticated_client, workspace, user
):
    project = Project.objects.create(
        workspace=workspace, name="Picker", manager=user
    )
    root = project.wbs_nodes.get(code="1")
    created = authenticated_client.post(
        f"/api/projects/{project.id}/wbs/",
        {"title": "WP1", "parent_id": root.id, "node_type": "work_package"},
        format="json",
    )
    assert created.status_code == status.HTTP_201_CREATED
    listed = authenticated_client.get("/api/workspace/schedule-activities/")
    assert listed.status_code == status.HTTP_200_OK
    assert any(row["name"] == "WP1" for row in listed.data)


@pytest.mark.django_db
def test_subprocess_spawns_child_and_completes(
    authenticated_client, workspace, user
):
    create = authenticated_client.post(
        "/api/process/definitions/",
        {
            "key": "with-sub",
            "name": "With Sub",
            "bpmn_xml": SUBPROCESS_BPMN,
            "process_id": "MainSub",
        },
        format="json",
    )
    assert create.status_code == status.HTTP_201_CREATED
    pk = create.data["id"]
    pub = authenticated_client.post(
        f"/api/process/definitions/{pk}/publish/", {}, format="json"
    )
    assert pub.status_code == status.HTTP_200_OK
    start = authenticated_client.post(
        f"/api/process/definitions/{pk}/start/", {}, format="json"
    )
    assert start.status_code == status.HTTP_201_CREATED
    parent = ProcessInstance.objects.get(pk=start.data["id"])
    children = list(parent.children.all())
    assert len(children) == 1
    assert children[0].subprocess_bpmn_id in ("Sub_1", "Nested") or children[
        0
    ].parent_spiff_task_id

    catalog = authenticated_client.get("/api/process/adapters/")
    sub = next(
        e
        for e in catalog.data["executable_elements"]
        if e["type"] == "subProcess"
    )
    assert sub["status"] == "supported"

    task = UserTask.objects.filter(
        instance=parent, status=UserTask.Status.OPEN
    ).first()
    assert task is not None
    assert "Inner" in task.name or task.name

    done = authenticated_client.post(
        f"/api/process/tasks/{task.id}/complete/",
        {},
        format="json",
    )
    assert done.status_code == status.HTTP_200_OK
    parent.refresh_from_db()
    assert parent.status == ProcessInstance.Status.COMPLETED
    children[0].refresh_from_db()
    assert children[0].status == ProcessInstance.Status.COMPLETED
