import pytest
from rest_framework import status

from process.lanes import extract_lanes
from process.models import ProcessDefinition, ProcessDefinitionLaneRole
from projects.models import Project, ProjectLessonsLearned


LANE_BPMN = """<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
  xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"
  id="Defs" targetNamespace="http://fastplan.local">
  <bpmn:process id="Proc_1" isExecutable="true">
    <bpmn:laneSet id="LaneSet_1">
      <bpmn:lane id="Lane_Sales" name="Sales">
        <bpmn:flowNodeRef>Task_1</bpmn:flowNodeRef>
      </bpmn:lane>
      <bpmn:lane id="Lane_Ops" name="Ops">
        <bpmn:flowNodeRef>Task_2</bpmn:flowNodeRef>
      </bpmn:lane>
    </bpmn:laneSet>
    <bpmn:startEvent id="Start_1"/>
    <bpmn:userTask id="Task_1" name="Qualify"/>
    <bpmn:userTask id="Task_2" name="Deliver"/>
    <bpmn:endEvent id="End_1"/>
  </bpmn:process>
</bpmn:definitions>
"""


@pytest.mark.django_db
def test_extract_lanes_from_bpmn():
    lanes = extract_lanes(LANE_BPMN)
    assert len(lanes) == 2
    assert lanes[0]["lane_id"] == "Lane_Sales"
    assert "Task_1" in lanes[0]["flow_node_refs"]


@pytest.mark.django_db
def test_lane_roles_crud(authenticated_client, workspace, user):
    definition = ProcessDefinition.objects.create(
        workspace=workspace,
        key="lane-raci",
        name="Lane RACI",
        bpmn_xml=LANE_BPMN,
        process_id="Proc_1",
        created_by=user,
    )
    listed = authenticated_client.get(f"/api/process/definitions/{definition.id}/lanes/")
    assert listed.status_code == status.HTTP_200_OK
    assert len(listed.data) == 2

    created = authenticated_client.post(
        f"/api/process/definitions/{definition.id}/lane-roles/",
        {
            "lane_id": "Lane_Sales",
            "lane_name": "Sales",
            "raci_type": "R",
            "role_key": "sales",
        },
        format="json",
    )
    assert created.status_code == status.HTTP_201_CREATED
    assert created.data["role_key"] == "sales"
    assert ProcessDefinitionLaneRole.objects.filter(definition=definition).count() == 1

    roles = authenticated_client.get(
        f"/api/process/definitions/{definition.id}/lane-roles/"
    )
    assert roles.status_code == status.HTTP_200_OK
    assert len(roles.data) == 1

    role_id = created.data["id"]
    deleted = authenticated_client.delete(f"/api/process/lane-roles/{role_id}/")
    assert deleted.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.django_db
def test_lessons_learned_get_patch_export(authenticated_client, workspace, user):
    project = Project.objects.create(
        workspace=workspace,
        name="Close Me",
        manager=user,
    )
    get_resp = authenticated_client.get(
        f"/api/projects/{project.id}/lessons-learned/"
    )
    assert get_resp.status_code == status.HTTP_200_OK
    assert "what_went_well" in get_resp.data

    patch = authenticated_client.patch(
        f"/api/projects/{project.id}/lessons-learned/",
        {
            "what_went_well": "Clear scope",
            "recommendations": "Keep weekly reviews",
        },
        format="json",
    )
    assert patch.status_code == status.HTTP_200_OK
    assert patch.data["what_went_well"] == "Clear scope"
    lessons = ProjectLessonsLearned.objects.get(project=project)
    assert lessons.recommendations == "Keep weekly reviews"

    md = authenticated_client.get(
        f"/api/projects/{project.id}/lessons-learned/export/?output=md"
    )
    assert md.status_code == status.HTTP_200_OK
    assert b"Clear scope" in md.content

    pdf = authenticated_client.get(
        f"/api/projects/{project.id}/lessons-learned/export/?output=pdf"
    )
    assert pdf.status_code == status.HTTP_200_OK
    assert pdf["Content-Type"] == "application/pdf"
