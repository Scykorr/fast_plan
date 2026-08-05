"""Scrum module: Product Backlog, Sprint activate/commit, burndown."""

from datetime import date, timedelta

import pytest
from rest_framework import status

from projects.models import Project
from scrum.models import ProductBacklogItem, ScrumSprint


@pytest.mark.django_db
def test_scrum_backlog_sprint_commit_activate(authenticated_client, workspace, user):
    project = Project.objects.create(
        workspace=workspace,
        name="Scrum project",
        manager=user,
        methodology=Project.Methodology.SCRUM,
    )
    pbi = authenticated_client.post(
        f"/api/projects/{project.id}/scrum/backlog/",
        {"title": "As a user I can login", "story_points": 5},
        format="json",
    )
    assert pbi.status_code == status.HTTP_201_CREATED
    pbi_id = pbi.data["id"]
    assert pbi.data["status"] == ProductBacklogItem.Status.TODO

    start = date.today()
    end = start + timedelta(days=13)
    sprint = authenticated_client.post(
        f"/api/projects/{project.id}/scrum/sprints/",
        {
            "name": "Sprint 1",
            "goal": "Auth done",
            "starts_on": start.isoformat(),
            "ends_on": end.isoformat(),
        },
        format="json",
    )
    assert sprint.status_code == status.HTTP_201_CREATED
    sprint_id = sprint.data["id"]
    assert sprint.data["status"] == ScrumSprint.Status.PLANNED

    commit = authenticated_client.post(
        f"/api/scrum/sprints/{sprint_id}/commit/",
        {"pbi_ids": [pbi_id]},
        format="json",
    )
    assert commit.status_code == status.HTTP_200_OK
    assert commit.data["committed"] == 1

    activate = authenticated_client.post(
        f"/api/scrum/sprints/{sprint_id}/activate/",
        {},
        format="json",
    )
    assert activate.status_code == status.HTTP_200_OK
    assert activate.data["status"] == ScrumSprint.Status.ACTIVE

    board = authenticated_client.get(f"/api/scrum/sprints/{sprint_id}/backlog/")
    assert board.status_code == status.HTTP_200_OK
    assert len(board.data) == 1

    patch = authenticated_client.patch(
        f"/api/scrum/pbis/{pbi_id}/",
        {"status": "done", "assignee_id": user.id},
        format="json",
    )
    assert patch.status_code == status.HTTP_200_OK
    assert patch.data["status"] == "done"
    assert patch.data["assignee_id"] == user.id

    burn = authenticated_client.get(f"/api/scrum/sprints/{sprint_id}/burndown/")
    assert burn.status_code == status.HTTP_200_OK
    assert burn.data["committed_points"] == 5
    assert len(burn.data["burndown"]) >= 1

    complete = authenticated_client.post(
        f"/api/scrum/sprints/{sprint_id}/complete/",
        {},
        format="json",
    )
    assert complete.status_code == status.HTTP_200_OK
    assert complete.data["status"] == ScrumSprint.Status.COMPLETED
