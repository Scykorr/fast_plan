"""P10 sprint 2: UserTask↔WBS binding + guest commercial portal."""

from decimal import Decimal

import pytest
from rest_framework import status

from crm.models import CrmDocument, CrmDocumentShareLink
from kanban.models import Card
from process.models import ProcessInstance, UserTask
from projects.models import Project, ScheduleActivity


SIMPLE_BPMN = """<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
  id="Defs_1" targetNamespace="http://fastplan.local/bpmn">
  <bpmn:process id="BindProcess" name="Bind" isExecutable="true">
    <bpmn:startEvent id="StartEvent_1" name="Start">
      <bpmn:outgoing>Flow_1</bpmn:outgoing>
    </bpmn:startEvent>
    <bpmn:userTask id="Activity_Approve" name="Approve">
      <bpmn:incoming>Flow_1</bpmn:incoming>
      <bpmn:outgoing>Flow_2</bpmn:outgoing>
    </bpmn:userTask>
    <bpmn:endEvent id="EndEvent_1" name="End">
      <bpmn:incoming>Flow_2</bpmn:incoming>
    </bpmn:endEvent>
    <bpmn:sequenceFlow id="Flow_1" sourceRef="StartEvent_1" targetRef="Activity_Approve" />
    <bpmn:sequenceFlow id="Flow_2" sourceRef="Activity_Approve" targetRef="EndEvent_1" />
  </bpmn:process>
</bpmn:definitions>
"""


@pytest.mark.django_db
def test_user_task_bind_wbs_completes_schedule_and_kanban(
    authenticated_client, workspace, user
):
    project = Project.objects.create(
        workspace=workspace,
        name="Delivery",
        manager=user,
    )
    root = project.wbs_nodes.get(code="1")
    wbs_resp = authenticated_client.post(
        f"/api/projects/{project.id}/wbs/",
        {
            "title": "Implement feature",
            "parent_id": root.id,
            "node_type": "work_package",
        },
        format="json",
    )
    assert wbs_resp.status_code == status.HTTP_201_CREATED
    from projects.models import WBSNode

    node = WBSNode.objects.get(project=project, title="Implement feature")
    node_id = node.id
    activity = ScheduleActivity.objects.get(wbs_node_id=node_id)
    card = Card.objects.get(wbs_node_id=node_id)
    todo_column = card.column
    done_column = card.column.board.columns.get(position=2)
    assert activity.progress == 0
    assert card.column_id == todo_column.id

    create = authenticated_client.post(
        "/api/process/definitions/",
        {
            "key": "bind-wbs",
            "name": "Bind WBS",
            "bpmn_xml": SIMPLE_BPMN,
            "process_id": "BindProcess",
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
        f"/api/process/definitions/{pk}/start/",
        {"project_id": project.id, "data": {}},
        format="json",
    )
    assert start.status_code == status.HTTP_201_CREATED
    assert start.data["project"] == project.id

    tasks = authenticated_client.get("/api/process/tasks/?status=open")
    assert tasks.status_code == status.HTTP_200_OK
    assert len(tasks.data) >= 1
    task = tasks.data[0]
    assert task["project"] == project.id

    bind = authenticated_client.patch(
        f"/api/process/tasks/{task['id']}/bind/",
        {"wbs_node_id": node_id},
        format="json",
    )
    assert bind.status_code == status.HTTP_200_OK
    assert bind.data["wbs_node"] == node_id
    assert bind.data["wbs_title"] == "Implement feature"

    done = authenticated_client.post(
        f"/api/process/tasks/{task['id']}/complete/",
        {"form_data": {"approved": True}},
        format="json",
    )
    assert done.status_code == status.HTTP_200_OK
    assert done.data["instance"]["status"] == ProcessInstance.Status.COMPLETED

    activity.refresh_from_db()
    card.refresh_from_db()
    assert activity.progress == 100
    assert card.column_id == done_column.id

    user_task = UserTask.objects.get(pk=task["id"])
    assert user_task.status == UserTask.Status.COMPLETED
    assert user_task.wbs_node_id == node_id


@pytest.mark.django_db
def test_guest_commercial_portal_view_approve_pdf(authenticated_client, workspace, user):
    doc = CrmDocument.objects.create(
        workspace=workspace,
        doc_type=CrmDocument.DocType.QUOTE,
        title="KP Demo",
        number="Q-100",
        status=CrmDocument.Status.SENT,
        amount=Decimal("1500.00"),
        currency="RUB",
        body="Please review",
        created_by=user,
    )
    create_link = authenticated_client.post(
        f"/api/crm/documents/{doc.id}/share-links/",
        {"label": "Client", "allow_approve": True, "allow_pdf": True},
        format="json",
    )
    assert create_link.status_code == status.HTTP_201_CREATED
    token = create_link.data["token"]
    assert create_link.data["url_path"] == f"/commerce/{token}"

    # Public client (no auth)
    from rest_framework.test import APIClient

    guest = APIClient()
    view = guest.get(f"/api/crm/share/{token}/")
    assert view.status_code == status.HTTP_200_OK
    assert view.data["document"]["title"] == "KP Demo"
    assert view.data["document"]["can_approve"] is True
    assert view.data["share"]["workspace_name"] == workspace.name

    approve = guest.post(f"/api/crm/share/{token}/approve/", {}, format="json")
    assert approve.status_code == status.HTTP_200_OK
    assert approve.data["document"]["status"] == CrmDocument.Status.ACCEPTED
    doc.refresh_from_db()
    assert doc.status == CrmDocument.Status.ACCEPTED

    pdf = guest.get(f"/api/crm/share/{token}/pdf/")
    assert pdf.status_code == status.HTTP_200_OK
    assert pdf["Content-Type"] == "application/pdf"
    assert pdf.content[:4] == b"%PDF"

    link = CrmDocumentShareLink.objects.get(token=token)
    revoke = authenticated_client.delete(
        f"/api/crm/documents/{doc.id}/share-links/{link.id}/"
    )
    assert revoke.status_code == status.HTTP_204_NO_CONTENT
    gone = guest.get(f"/api/crm/share/{token}/")
    assert gone.status_code == status.HTTP_404_NOT_FOUND
