"""Process-as-WBS materialize + BANT qualification."""

from pathlib import Path

import pytest
from rest_framework import status

from process.models import ProcessWorkNode

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
