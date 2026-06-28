import pytest
from datetime import date
from rest_framework import status

from projects.models import Project, ScheduleActivity


@pytest.fixture
def project(workspace, user):
    return Project.objects.create(
        workspace=workspace,
        name="Website Redesign",
        description="PMBOK test project",
        manager=user,
    )


@pytest.mark.django_db
def test_move_card_syncs_activity_progress(authenticated_client, project):
    root = project.wbs_nodes.get(code="1")
    authenticated_client.post(
        f"/api/projects/{project.id}/wbs/",
        {"title": "Task C", "parent_id": root.id, "node_type": "work_package"},
        format="json",
    )
    activity = ScheduleActivity.objects.get(wbs_node__title="Task C")
    card = activity.wbs_node.card
    done_column = card.column.board.columns.get(position=2)

    response = authenticated_client.post(
        f"/api/cards/{card.id}/move/",
        {"column_id": done_column.id, "position": 0},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    activity.refresh_from_db()
    assert activity.progress == 100


@pytest.mark.django_db
def test_move_card_to_in_progress_sets_partial_progress(authenticated_client, project):
    root = project.wbs_nodes.get(code="1")
    authenticated_client.post(
        f"/api/projects/{project.id}/wbs/",
        {"title": "Task D", "parent_id": root.id, "node_type": "work_package"},
        format="json",
    )
    activity = ScheduleActivity.objects.get(wbs_node__title="Task D")
    card = activity.wbs_node.card
    in_progress_column = card.column.board.columns.get(position=1)

    response = authenticated_client.post(
        f"/api/cards/{card.id}/move/",
        {"column_id": in_progress_column.id, "position": 0},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    activity.refresh_from_db()
    assert activity.progress == 50


@pytest.mark.django_db
def test_project_calendar_returns_milestones(authenticated_client, project):
    root = project.wbs_nodes.get(code="1")
    authenticated_client.post(
        f"/api/projects/{project.id}/wbs/",
        {
            "title": "Go live",
            "parent_id": root.id,
            "node_type": "milestone",
        },
        format="json",
    )
    activity = ScheduleActivity.objects.get(wbs_node__title="Go live")
    activity.start_date = date(2026, 6, 15)
    activity.save(update_fields=["start_date"])

    response = authenticated_client.get(
        f"/api/projects/{project.id}/calendar/?year=2026&month=6"
    )
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 1
    assert "Go live" in response.data[0]["title"]
    assert response.data[0]["extendedProps"]["event_type"] == "milestone"


@pytest.mark.django_db
def test_workspace_milestones_calendar(authenticated_client, project):
    root = project.wbs_nodes.get(code="1")
    authenticated_client.post(
        f"/api/projects/{project.id}/wbs/",
        {
            "title": "Release",
            "parent_id": root.id,
            "node_type": "milestone",
        },
        format="json",
    )
    activity = ScheduleActivity.objects.get(wbs_node__title="Release")
    activity.start_date = date(2026, 7, 1)
    activity.save(update_fields=["start_date"])

    response = authenticated_client.get("/api/calendar/milestones/?year=2026&month=7")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 1
    assert response.data[0]["extendedProps"]["project_id"] == project.id
