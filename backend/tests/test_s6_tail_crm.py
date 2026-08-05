"""S6 tail (capacity/CSV/comments/DnD) + CRM Quote→WBS + health."""

from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from rest_framework import status

from crm.models import CrmDocument, Deal, Organization
from crm.services import ensure_default_pipeline
from process.models import ProcessWorkNode
from projects.models import WorkItemComment, WBSNode

PRINCE_BPMN = (
    Path(__file__).resolve().parents[1] / "process" / "packs" / "prince2_stage.bpmn"
)


def _start_materialized(client):
    xml = PRINCE_BPMN.read_text(encoding="utf-8")
    create = client.post(
        "/api/process/definitions/",
        {
            "key": "s6-tail",
            "name": "S6 tail",
            "bpmn_xml": xml,
            "process_id": "Prince2Stage",
        },
        format="json",
    )
    assert create.status_code == status.HTTP_201_CREATED
    pk = create.data["id"]
    client.post(f"/api/process/definitions/{pk}/publish/", {}, format="json")
    start = client.post(
        f"/api/process/definitions/{pk}/start/",
        {"data": {}},
        format="json",
    )
    instance_id = start.data["id"]
    mat = client.post(
        f"/api/process/instances/{instance_id}/materialize-wbs/",
        {},
        format="json",
    )
    assert mat.status_code == status.HTTP_200_OK
    return instance_id


@pytest.mark.django_db
def test_process_work_tree_capacity_csv_comments_reorder(
    authenticated_client, workspace, user
):
    instance_id = _start_materialized(authenticated_client)
    node = ProcessWorkNode.objects.filter(
        instance_id=instance_id, node_type=ProcessWorkNode.NodeType.USER_TASK
    ).first()
    assert node is not None
    node.assignee = user
    node.save(update_fields=["assignee"])

    detail = authenticated_client.get(f"/api/process/instances/{instance_id}/")
    assert detail.status_code == status.HTTP_200_OK

    def find(nodes, nid):
        for n in nodes:
            if n["id"] == nid:
                return n
            found = find(n.get("children") or [], nid)
            if found:
                return found
        return None

    serialized = find(detail.data["work_tree"], node.id)
    assert serialized is not None
    assert "capacity_hint" in serialized

    csv_resp = authenticated_client.get(
        f"/api/process/instances/{instance_id}/work-tree/export/?output=csv"
    )
    assert csv_resp.status_code == status.HTTP_200_OK
    assert "text/csv" in csv_resp["Content-Type"]
    assert b"code" in csv_resp.content

    comment = authenticated_client.post(
        f"/api/process/work-nodes/{node.id}/comments/",
        {"body": "hello process", "kind": "comment"},
        format="json",
    )
    assert comment.status_code == status.HTTP_201_CREATED
    assert WorkItemComment.objects.filter(process_work_node=node).count() == 1

    siblings = list(
        ProcessWorkNode.objects.filter(
            instance_id=instance_id, parent_id=node.parent_id
        ).order_by("position", "id")
    )
    if len(siblings) >= 2:
        target = siblings[0]
        moved = authenticated_client.patch(
            f"/api/process/work-nodes/{siblings[-1].id}/",
            {"position": 0},
            format="json",
        )
        assert moved.status_code == status.HTTP_200_OK
        siblings[-1].refresh_from_db()
        assert siblings[-1].position == 0
        target.refresh_from_db()


@pytest.mark.django_db
def test_quote_to_wbs_and_crm_health(authenticated_client, workspace, user):
    pipeline = ensure_default_pipeline(workspace)
    stage = pipeline.stages.order_by("position").first()
    org = Organization.objects.create(workspace=workspace, name="Health Co")
    deal = Deal.objects.create(
        workspace=workspace,
        pipeline=pipeline,
        stage=stage,
        title="Quote deal",
        amount=Decimal("5000"),
        organization=org,
        owner=user,
        bant_budget=True,
        bant_need=True,
    )
    doc = CrmDocument.objects.create(
        workspace=workspace,
        doc_type=CrmDocument.DocType.QUOTE,
        title="KP demo",
        deal=deal,
        organization=org,
        line_items=[
            {"title": "Discovery", "qty": 1, "price": 1000},
            {"title": "Delivery", "qty": 1, "price": 4000},
        ],
        amount=Decimal("5000"),
        created_by=user,
    )
    resp = authenticated_client.post(
        f"/api/crm/documents/{doc.id}/create-wbs/",
        {},
        format="json",
    )
    assert resp.status_code == status.HTTP_201_CREATED
    assert resp.data["created_count"] == 2
    assert resp.data["project_id"]
    doc.refresh_from_db()
    assert doc.project_id == resp.data["project_id"]
    assert (
        WBSNode.objects.filter(project_id=resp.data["project_id"]).count() >= 3
    )

    CrmDocument.objects.create(
        workspace=workspace,
        doc_type=CrmDocument.DocType.INVOICE,
        title="Overdue inv",
        deal=deal,
        organization=org,
        status=CrmDocument.Status.SENT,
        due_date=date.today() - timedelta(days=10),
        amount=Decimal("100"),
        created_by=user,
    )
    health = authenticated_client.get(f"/api/crm/health/?deal_id={deal.id}")
    assert health.status_code == status.HTTP_200_OK
    assert "score" in health.data
    assert health.data["band"] in ("healthy", "watch", "at_risk")
    assert health.data["deal_id"] == deal.id

    org_health = authenticated_client.get(
        f"/api/crm/health/?organization_id={org.id}"
    )
    assert org_health.status_code == status.HTTP_200_OK
    assert org_health.data["organization_id"] == org.id
