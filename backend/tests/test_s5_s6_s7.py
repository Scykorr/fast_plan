"""Process-as-WBS materialize + BANT qualification + S6 deepen."""

from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status

from kanban.models import Board, Card
from process.models import ProcessWorkNode
from timelog.models import TimeEntry

PRINCE_BPMN = (
    Path(__file__).resolve().parents[1] / "process" / "packs" / "prince2_stage.bpmn"
)


@pytest.mark.django_db
def test_materialize_process_work_tree(authenticated_client, workspace, user):
    xml = PRINCE_BPMN.read_text(encoding="utf-8")
    create = authenticated_client.post(
        "/api/process/definitions/",
        {
            "key": "prince2-demo",
            "name": "PRINCE2 demo",
            "bpmn_xml": xml,
            "process_id": "Prince2Stage",
        },
        format="json",
    )
    assert create.status_code == status.HTTP_201_CREATED
    pk = create.data["id"]
    authenticated_client.post(f"/api/process/definitions/{pk}/publish/", {}, format="json")
    start = authenticated_client.post(
        f"/api/process/definitions/{pk}/start/",
        {"data": {}},
        format="json",
    )
    assert start.status_code == status.HTTP_201_CREATED
    instance_id = start.data["id"]

    mat = authenticated_client.post(
        f"/api/process/instances/{instance_id}/materialize-wbs/",
        {},
        format="json",
    )
    assert mat.status_code == status.HTTP_200_OK
    assert mat.data["created"] >= 4
    assert mat.data["tree"]
    assert ProcessWorkNode.objects.filter(instance_id=instance_id).count() >= 4

    detail = authenticated_client.get(f"/api/process/instances/{instance_id}/")
    assert detail.status_code == status.HTTP_200_OK
    assert detail.data["work_tree"]

    node = ProcessWorkNode.objects.filter(
        instance_id=instance_id, node_type=ProcessWorkNode.NodeType.USER_TASK
    ).first()
    assert node is not None
    patched = authenticated_client.patch(
        f"/api/process/work-nodes/{node.id}/",
        {
            "raci_r": "Analyst",
            "raci_a": "PM",
            "duration_days": 3,
            "start_date": "2026-08-01",
            "end_date": "2026-08-03",
        },
        format="json",
    )
    assert patched.status_code == status.HTTP_200_OK
    node.refresh_from_db()
    assert node.raci_r == "Analyst"
    assert node.duration_days == 3


@pytest.mark.django_db
def test_process_work_kanban_time_attachments(authenticated_client, workspace, user):
    xml = PRINCE_BPMN.read_text(encoding="utf-8")
    create = authenticated_client.post(
        "/api/process/definitions/",
        {
            "key": "prince2-s6",
            "name": "PRINCE2 S6",
            "bpmn_xml": xml,
            "process_id": "Prince2Stage",
        },
        format="json",
    )
    assert create.status_code == status.HTTP_201_CREATED
    pk = create.data["id"]
    authenticated_client.post(f"/api/process/definitions/{pk}/publish/", {}, format="json")
    start = authenticated_client.post(
        f"/api/process/definitions/{pk}/start/",
        {"data": {}},
        format="json",
    )
    instance_id = start.data["id"]
    mat = authenticated_client.post(
        f"/api/process/instances/{instance_id}/materialize-wbs/",
        {},
        format="json",
    )
    assert mat.status_code == status.HTTP_200_OK
    assert mat.data.get("board_id")
    assert Board.objects.filter(process_instance_id=instance_id).exists()

    node = ProcessWorkNode.objects.filter(
        instance_id=instance_id, node_type=ProcessWorkNode.NodeType.USER_TASK
    ).first()
    assert node is not None
    assert Card.objects.filter(process_work_node=node).exists()

    time_resp = authenticated_client.post(
        "/api/workspace/time-entries/",
        {
            "process_work_node": node.id,
            "hours": "1.50",
            "work_date": "2026-08-04",
            "notes": "review",
        },
        format="json",
    )
    assert time_resp.status_code == status.HTTP_201_CREATED
    assert TimeEntry.objects.filter(process_work_node=node).count() == 1

    upload = SimpleUploadedFile(
        "note.txt",
        b"hello process",
        content_type="text/plain",
    )
    att = authenticated_client.post(
        f"/api/process/work-nodes/{node.id}/attachments/",
        {"file": upload},
        format="multipart",
    )
    assert att.status_code == status.HTTP_201_CREATED
    assert att.data["process_work_node_id"] == node.id

    tree = authenticated_client.get(f"/api/process/instances/{instance_id}/")
    assert tree.status_code == status.HTTP_200_OK

    def find(nodes, nid):
        for n in nodes:
            if n["id"] == nid:
                return n
            found = find(n.get("children") or [], nid)
            if found:
                return found
        return None

    serialized = find(tree.data["work_tree"], node.id)
    assert serialized is not None
    assert serialized["card_id"]
    assert serialized["board_id"]
    assert serialized["attachment_count"] == 1
    assert float(serialized["time_hours"]) == 1.5

    card = Card.objects.get(process_work_node=node)
    done_col = card.column.board.columns.order_by("position").last()
    move = authenticated_client.post(
        f"/api/cards/{card.id}/move/",
        {"column_id": done_col.id, "position": 0},
        format="json",
    )
    assert move.status_code == status.HTTP_200_OK
    node.refresh_from_db()
    assert node.status == ProcessWorkNode.Status.DONE
    assert node.progress == 100


@pytest.mark.django_db
def test_deal_bant_qualification_score(authenticated_client, workspace, user):
    from crm.models import Deal, Pipeline, PipelineStage

    pipeline = Pipeline.objects.create(workspace=workspace, name="Sales")
    stage = PipelineStage.objects.create(
        pipeline=pipeline,
        name="Qualify",
        position=1,
        playbook_checklist=["Discovery call", "Send deck"],
    )
    deal = Deal.objects.create(
        workspace=workspace,
        pipeline=pipeline,
        stage=stage,
        title="BANT deal",
        amount=1000,
        owner=user,
    )
    resp = authenticated_client.patch(
        f"/api/crm/deals/{deal.id}/",
        {
            "bant_budget": True,
            "bant_need": True,
            "playbook_done": ["Discovery call"],
        },
        format="json",
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["qualification_score"] == 50
    assert resp.data["bant_budget"] is True
    assert "Discovery call" in resp.data["playbook_done"]
    assert "Discovery call" in resp.data["stage_playbook"]


@pytest.mark.django_db
def test_methodology_packs_listed(authenticated_client, workspace):
    packs = authenticated_client.get("/api/process/packs/")
    assert packs.status_code == status.HTTP_200_OK
    ids = {p["id"] for p in packs.data}
    assert "prince2_stage" in ids
    assert "scrum_ceremony" in ids
