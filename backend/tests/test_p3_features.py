from datetime import date, timedelta

import pytest
from rest_framework import status

from projects.models import Project, ScheduleActivity, WBSNode, WorkItemComment
from tests.factories import ProjectFactory


@pytest.fixture
def project(workspace, user):
    return Project.objects.create(
        workspace=workspace,
        name="P3 Project",
        manager=user,
        budget=10000,
    )


@pytest.mark.django_db
def test_project_export_pdf(authenticated_client, project):
    response = authenticated_client.get(
        f"/api/projects/{project.id}/export/?output=pdf"
    )
    assert response.status_code == status.HTTP_200_OK
    assert response["Content-Type"] == "application/pdf"
    assert response.content[:4] == b"%PDF"


@pytest.mark.django_db
def test_wbs_comments_create_and_list(authenticated_client, project, user):
    root = project.wbs_nodes.get(code="1")
    created = authenticated_client.post(
        f"/api/wbs/{root.id}/comments/",
        {"body": "Go with option A", "kind": "decision"},
        format="json",
    )
    assert created.status_code == status.HTTP_201_CREATED
    assert created.data["kind"] == "decision"
    listed = authenticated_client.get(f"/api/wbs/{root.id}/comments/")
    assert listed.status_code == status.HTTP_200_OK
    assert len(listed.data) == 1
    assert WorkItemComment.objects.filter(wbs_node=root).count() == 1


@pytest.mark.django_db
def test_workspace_search_finds_project(authenticated_client, workspace, user):
    ProjectFactory(workspace=workspace, manager=user, name="Apollo Mission")
    response = authenticated_client.get("/api/workspace/search/?q=Apollo")
    assert response.status_code == status.HTTP_200_OK
    titles = [item["title"] for item in response.data["results"]]
    assert any("Apollo" in title for title in titles)


@pytest.mark.django_db
def test_my_tasks_returns_assigned_wbs(authenticated_client, workspace, user):
    project = ProjectFactory(workspace=workspace, manager=user, name="Tasks Proj")
    root = project.wbs_nodes.get(code="1")
    node = WBSNode.objects.create(
        project=project,
        parent=root,
        title="Mine",
        code="1.1",
        node_type=WBSNode.NodeType.WORK_PACKAGE,
        position=0,
        assignee=user,
    )
    ScheduleActivity.objects.create(
        wbs_node=node,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=2),
        progress=10,
    )
    response = authenticated_client.get("/api/workspace/my-tasks/")
    assert response.status_code == status.HTTP_200_OK
    assert response.data["summary"]["total"] >= 1
    assert any(item["wbs_id"] == node.id for item in response.data["tasks"])


@pytest.mark.django_db
def test_capacity_report(authenticated_client, workspace, user):
    project = ProjectFactory(workspace=workspace, manager=user, name="Cap Proj")
    root = project.wbs_nodes.get(code="1")
    node = WBSNode.objects.create(
        project=project,
        parent=root,
        title="Load",
        code="1.1",
        node_type=WBSNode.NodeType.WORK_PACKAGE,
        position=0,
        assignee=user,
    )
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    ScheduleActivity.objects.create(
        wbs_node=node,
        start_date=week_start,
        end_date=week_start + timedelta(days=2),
        progress=0,
    )
    response = authenticated_client.get(
        f"/api/workspace/capacity/?week_start={week_start.isoformat()}"
    )
    assert response.status_code == status.HTTP_200_OK
    member = next(
        item for item in response.data["members"] if item["user_id"] == user.id
    )
    assert member["allocated_hours"] > 0
