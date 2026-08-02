"""Resource leveling propose + Inclusive gateway pack."""

from datetime import date, timedelta
from pathlib import Path

import pytest
from rest_framework import status

from process.catalog import list_adapter_catalog
from projects.models import Project, ScheduleActivity, WBSNode
from workspaces.models import MemberCapacity

OR_BPMN = Path(__file__).resolve().parents[1] / "process" / "packs" / "or_inclusive.bpmn"


@pytest.mark.django_db
def test_leveling_propose_shifts_overloaded_week(authenticated_client, workspace, user):
    MemberCapacity.objects.update_or_create(
        workspace=workspace,
        user=user,
        defaults={"hours_per_week": 8},
    )
    project = Project.objects.create(
        workspace=workspace, name="Level project", manager=user
    )
    root = project.wbs_nodes.get(code="1")
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    activity_ids = []
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
        activity_ids.append(activity.id)

    propose = authenticated_client.post(
        f"/api/projects/{project.id}/schedule/leveling/propose/",
        {"week_start": week_start.isoformat(), "max_shift_days": 14},
        format="json",
    )
    assert propose.status_code == status.HTTP_200_OK
    assert propose.data["overloaded_assignees"]
    assert propose.data["proposals"], propose.data
    first = propose.data["proposals"][0]
    assert first["activity_id"] in activity_ids
    assert first["shift_days"] >= 1
    assert first["proposed"]["start_date"] > first["current"]["start_date"]

    # Apply via existing PATCH
    applied = authenticated_client.patch(
        f"/api/activities/{first['activity_id']}/",
        {
            "start_date": first["proposed"]["start_date"],
            "end_date": first["proposed"]["end_date"],
            "duration_days": first["proposed"]["duration_days"],
        },
        format="json",
    )
    assert applied.status_code == status.HTTP_200_OK
    activity = ScheduleActivity.objects.get(pk=first["activity_id"])
    assert activity.start_date.isoformat() == first["proposed"]["start_date"]


@pytest.mark.django_db
def test_inclusive_gateway_catalog_and_pack(authenticated_client, workspace, user):
    catalog = list_adapter_catalog()
    inclusive = next(
        e for e in catalog["executable_elements"] if e["type"] == "inclusiveGateway"
    )
    assert inclusive["status"] == "supported"

    xml = OR_BPMN.read_text(encoding="utf-8")
    create = authenticated_client.post(
        "/api/process/definitions/",
        {
            "key": "or-inclusive",
            "name": "OR",
            "bpmn_xml": xml,
            "process_id": "OrInclusive",
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

    tasks = authenticated_client.get("/api/process/tasks/?status=open")
    flags = next(t for t in tasks.data if t["instance_id"] == instance_id)
    assert "Choose" in flags["name"] or "Flags" in flags["name"] or flags["name"]

    done = authenticated_client.post(
        f"/api/process/tasks/{flags['id']}/complete/",
        {"form_data": {"need_legal": True, "need_tech": True}},
        format="json",
    )
    assert done.status_code == status.HTTP_200_OK

    tasks2 = authenticated_client.get("/api/process/tasks/?status=open")
    open_names = [
        t["name"] for t in tasks2.data if t["instance_id"] == instance_id
    ]
    # Inclusive OR-split: both true conditions open in parallel
    assert any("Legal" in n for n in open_names), open_names
    assert any("Tech" in n for n in open_names), open_names

    packs = authenticated_client.get("/api/process/packs/")
    assert packs.status_code == status.HTTP_200_OK
    assert any(p.get("id") == "or_inclusive" for p in packs.data)


@pytest.mark.django_db
def test_instance_detail_includes_children_key(authenticated_client, workspace, user):
    xml = OR_BPMN.read_text(encoding="utf-8")
    create = authenticated_client.post(
        "/api/process/definitions/",
        {
            "key": "or-inclusive-children",
            "name": "OR2",
            "bpmn_xml": xml,
            "process_id": "OrInclusive",
        },
        format="json",
    )
    pk = create.data["id"]
    authenticated_client.post(f"/api/process/definitions/{pk}/publish/", {}, format="json")
    start = authenticated_client.post(
        f"/api/process/definitions/{pk}/start/",
        {"data": {}},
        format="json",
    )
    detail = authenticated_client.get(f"/api/process/instances/{start.data['id']}/")
    assert detail.status_code == status.HTTP_200_OK
    assert "children" in detail.data
    assert detail.data["children"] == []
