"""S1/S2/S4: PERT Monte Carlo, leveling apply/undo, migrate publish, SMTP go-live."""

from datetime import date, timedelta

import pytest
from rest_framework import status

from process.models import ProcessInstance
from projects.models import Project, ScheduleActivity, WBSNode
from projects.pert import compute_pert_network
from workspaces.models import MemberCapacity


@pytest.fixture
def project(workspace, user):
    return Project.objects.create(
        workspace=workspace, name="Sprint PERT", manager=user
    )


SIMPLE_BPMN_V1 = """<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
  id="Defs" targetNamespace="http://fastplan.local/bpmn">
  <bpmn:process id="MigProc" name="Mig" isExecutable="true">
    <bpmn:startEvent id="Start_1"><bpmn:outgoing>f1</bpmn:outgoing></bpmn:startEvent>
    <bpmn:userTask id="Task_A" name="Review A">
      <bpmn:incoming>f1</bpmn:incoming>
      <bpmn:outgoing>f2</bpmn:outgoing>
    </bpmn:userTask>
    <bpmn:endEvent id="End_1"><bpmn:incoming>f2</bpmn:incoming></bpmn:endEvent>
    <bpmn:sequenceFlow id="f1" sourceRef="Start_1" targetRef="Task_A"/>
    <bpmn:sequenceFlow id="f2" sourceRef="Task_A" targetRef="End_1"/>
  </bpmn:process>
</bpmn:definitions>
"""

SIMPLE_BPMN_V2 = """<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
  id="Defs" targetNamespace="http://fastplan.local/bpmn">
  <bpmn:process id="MigProc" name="Mig" isExecutable="true">
    <bpmn:startEvent id="Start_1"><bpmn:outgoing>f1</bpmn:outgoing></bpmn:startEvent>
    <bpmn:userTask id="Task_A" name="Review A v2">
      <bpmn:incoming>f1</bpmn:incoming>
      <bpmn:outgoing>f2</bpmn:outgoing>
    </bpmn:userTask>
    <bpmn:userTask id="Task_B" name="Extra">
      <bpmn:incoming>f2</bpmn:incoming>
      <bpmn:outgoing>f3</bpmn:outgoing>
    </bpmn:userTask>
    <bpmn:endEvent id="End_1"><bpmn:incoming>f3</bpmn:incoming></bpmn:endEvent>
    <bpmn:sequenceFlow id="f1" sourceRef="Start_1" targetRef="Task_A"/>
    <bpmn:sequenceFlow id="f2" sourceRef="Task_A" targetRef="Task_B"/>
    <bpmn:sequenceFlow id="f3" sourceRef="Task_B" targetRef="End_1"/>
  </bpmn:process>
</bpmn:definitions>
"""


@pytest.mark.django_db
def test_pert_monte_carlo_api(authenticated_client, project):
    root = project.wbs_nodes.get(code="1")
    authenticated_client.post(
        f"/api/projects/{project.id}/wbs/",
        {"title": "MC Task", "parent_id": root.id, "node_type": "work_package"},
        format="json",
    )
    response = authenticated_client.get(
        f"/api/projects/{project.id}/pert/?method=monte_carlo&trials=200"
    )
    assert response.status_code == status.HTTP_200_OK
    finish = response.data["finish"]
    assert finish["method"] == "monte_carlo"
    assert finish["trials"] == 200
    assert finish["p10_days"] <= finish["p50_days"] <= finish["p90_days"]


@pytest.mark.django_db
def test_pert_monte_carlo_deterministic(project):
    from projects.services import create_work_package

    root = project.wbs_nodes.get(code="1")
    create_work_package(
        project, root, "A", with_schedule=True, with_kanban_card=False
    )
    a = compute_pert_network(project, method="monte_carlo", trials=100)
    b = compute_pert_network(project, method="monte_carlo", trials=100)
    assert a["finish"] == b["finish"]


@pytest.mark.django_db
def test_leveling_apply_all_and_undo(authenticated_client, workspace, user):
    MemberCapacity.objects.update_or_create(
        workspace=workspace,
        user=user,
        defaults={"hours_per_week": 8},
    )
    project = Project.objects.create(
        workspace=workspace, name="Apply leveling", manager=user
    )
    root = project.wbs_nodes.get(code="1")
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    proposals_payload = []
    for title in ("Task A", "Task B"):
        resp = authenticated_client.post(
            f"/api/projects/{project.id}/wbs/",
            {
                "title": title,
                "parent_id": root.id,
                "node_type": "work_package",
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED
        node = WBSNode.objects.get(project=project, title=title)
        node.assignee = user
        node.save(update_fields=["assignee"])
        activity = ScheduleActivity.objects.get(wbs_node=node)
        activity.start_date = week_start
        activity.end_date = week_start + timedelta(days=4)
        activity.progress = 0
        activity.save(update_fields=["start_date", "end_date", "progress"])

    propose = authenticated_client.post(
        f"/api/projects/{project.id}/schedule/leveling/propose/",
        {"week_start": week_start.isoformat(), "max_shift_days": 14},
        format="json",
    )
    assert propose.status_code == status.HTTP_200_OK
    assert propose.data["proposals"]
    proposals_payload = propose.data["proposals"]

    applied = authenticated_client.post(
        f"/api/projects/{project.id}/schedule/leveling/apply/",
        {"proposals": proposals_payload},
        format="json",
    )
    assert applied.status_code == status.HTTP_200_OK
    assert applied.data["applied"]
    batch = applied.data["batch"]
    assert batch["items"]

    first_id = proposals_payload[0]["activity_id"]
    activity = ScheduleActivity.objects.get(pk=first_id)
    assert activity.start_date.isoformat() == proposals_payload[0]["proposed"]["start_date"]

    undo = authenticated_client.post(
        f"/api/projects/{project.id}/schedule/leveling/undo/",
        {"items": batch["items"]},
        format="json",
    )
    assert undo.status_code == status.HTTP_200_OK
    assert undo.data["count"] >= 1
    restored = ScheduleActivity.objects.get(pk=first_id)
    assert restored.start_date.isoformat() == proposals_payload[0]["current"]["start_date"]


@pytest.mark.django_db
def test_publish_migrate_running_instances(authenticated_client, workspace, user):
    create = authenticated_client.post(
        "/api/process/definitions/",
        {
            "key": "mig-proc",
            "name": "Migrate",
            "bpmn_xml": SIMPLE_BPMN_V1,
            "process_id": "MigProc",
        },
        format="json",
    )
    assert create.status_code == status.HTTP_201_CREATED
    pk = create.data["id"]
    authenticated_client.post(
        f"/api/process/definitions/{pk}/publish/", {}, format="json"
    )
    start = authenticated_client.post(
        f"/api/process/definitions/{pk}/start/",
        {"data": {}},
        format="json",
    )
    assert start.status_code == status.HTTP_201_CREATED
    instance_id = start.data["id"]
    old_deployment = ProcessInstance.objects.get(pk=instance_id).deployment_id

    patch = authenticated_client.patch(
        f"/api/process/definitions/{pk}/",
        {"bpmn_xml": SIMPLE_BPMN_V2},
        format="json",
    )
    assert patch.status_code == status.HTTP_200_OK

    published = authenticated_client.post(
        f"/api/process/definitions/{pk}/publish/",
        {"migrate_running": True},
        format="json",
    )
    assert published.status_code == status.HTTP_200_OK
    mig = published.data["migration"]
    assert mig["migrated_count"] >= 1
    instance = ProcessInstance.objects.get(pk=instance_id)
    assert instance.deployment_id != old_deployment
    assert instance.deployment_id == published.data["deployment_id"]


@pytest.mark.django_db
def test_email_go_live_ready_and_health(authenticated_client, api_client, settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    settings.EMAIL_HOST = "smtp.example.com"
    settings.EMAIL_PORT = 587
    settings.EMAIL_HOST_USER = "mailer"
    settings.DEFAULT_FROM_EMAIL = "noreply@example.com"
    settings.REQUIRE_EMAIL_VERIFICATION = False

    status_resp = authenticated_client.get("/api/workspace/email/status/")
    assert status_resp.status_code == status.HTTP_200_OK
    assert status_resp.data["go_live_ready"] is True
    assert status_resp.data["configured"] is True

    health = api_client.get("/api/health/?extended=1")
    assert health.status_code == 200
    email = health.data["checks"]["email"]
    assert email["configured"] is True
    assert email["status"] == "ok"

    settings.REQUIRE_EMAIL_VERIFICATION = True
    settings.EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
    settings.EMAIL_HOST = ""
    warn = api_client.get("/api/health/?extended=1")
    assert warn.data["checks"]["email"]["status"] == "warn"
