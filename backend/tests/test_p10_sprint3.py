"""P10 sprint 3: capacity schedule hints + Org/Person merge."""

from datetime import date, timedelta

import pytest
from django.utils import timezone
from rest_framework import status

from crm.models import Activity, Organization, Person
from projects.models import Project, ScheduleActivity, WBSNode
from workspaces.models import MemberCapacity


@pytest.mark.django_db
def test_schedule_capacity_hints_mark_overloaded_assignee(
    authenticated_client, workspace, user
):
    MemberCapacity.objects.update_or_create(
        workspace=workspace,
        user=user,
        defaults={"hours_per_week": 8},
    )
    project = Project.objects.create(
        workspace=workspace, name="Cap project", manager=user
    )
    root = project.wbs_nodes.get(code="1")
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
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

    schedule = authenticated_client.get(f"/api/projects/{project.id}/schedule/")
    assert schedule.status_code == status.HTTP_200_OK
    assert len(schedule.data["activities"]) >= 2
    overloaded = [
        row for row in schedule.data["activities"] if row.get("capacity_hint")
    ]
    assert overloaded
    assert all(row["capacity_hint"]["overloaded"] is True for row in overloaded)
    assert all(row["assignee_id"] == user.id for row in overloaded)

    wbs = authenticated_client.get(f"/api/projects/{project.id}/wbs/")
    assert wbs.status_code == status.HTTP_200_OK

    def find_hint(nodes):
        for node in nodes:
            if node["title"] == "Task A":
                return node.get("capacity_hint")
            child = find_hint(node.get("children") or [])
            if child is not None:
                return child
        return None

    hint = find_hint(wbs.data)
    assert hint is not None
    assert hint["overloaded"] is True


@pytest.mark.django_db
def test_person_duplicates_and_merge(authenticated_client, workspace, user):
    survivor = Person.objects.create(
        workspace=workspace,
        full_name="Alice Primary",
        email="alice@example.com",
        phone="",
        owner=user,
    )
    source = Person.objects.create(
        workspace=workspace,
        full_name="Alice Dup",
        email="alice@example.com",
        phone="+7 (999) 111-22-33",
        notes="from channel",
        owner=user,
    )
    Activity.objects.create(
        workspace=workspace,
        person=source,
        kind=Activity.Kind.NOTE,
        subject="Touch from duplicate",
        occurred_at=timezone.now(),
        created_by=user,
    )

    dupes = authenticated_client.get("/api/crm/people/duplicates/")
    assert dupes.status_code == status.HTTP_200_OK
    assert any(
        g["reason"] == "email" and {g["survivor_id"], g["source_id"]} == {survivor.id, source.id}
        for g in dupes.data["groups"]
    )

    merged = authenticated_client.post(
        f"/api/crm/people/{survivor.id}/merge/",
        {"source_id": source.id},
        format="json",
    )
    assert merged.status_code == status.HTTP_200_OK
    assert merged.data["id"] == survivor.id
    assert merged.data["phone"] == "+7 (999) 111-22-33"
    assert merged.data["notes"] == "from channel"
    assert not Person.objects.filter(pk=source.id).exists()
    assert Activity.objects.filter(person=survivor, subject="Touch from duplicate").exists()


@pytest.mark.django_db
def test_organization_duplicates_and_merge(authenticated_client, workspace, user):
    survivor = Organization.objects.create(
        workspace=workspace,
        name="Acme Surv",
        website="https://acme.example",
        owner=user,
    )
    source = Organization.objects.create(
        workspace=workspace,
        name="Acme Source",
        website="https://acme.example/",
        industry="IT",
        owner=user,
    )
    Activity.objects.create(
        workspace=workspace,
        organization=source,
        kind=Activity.Kind.CALL,
        subject="Sales call",
        occurred_at=timezone.now(),
        created_by=user,
    )

    dupes = authenticated_client.get("/api/crm/organizations/duplicates/")
    assert dupes.status_code == status.HTTP_200_OK
    assert any(g["reason"] == "website" for g in dupes.data["groups"])

    merged = authenticated_client.post(
        f"/api/crm/organizations/{survivor.id}/merge/",
        {"source_id": source.id},
        format="json",
    )
    assert merged.status_code == status.HTTP_200_OK
    assert merged.data["id"] == survivor.id
    assert merged.data["industry"] == "IT"
    assert not Organization.objects.filter(pk=source.id).exists()
    assert Activity.objects.filter(
        organization=survivor, subject="Sales call"
    ).exists()
