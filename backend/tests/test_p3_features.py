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
def test_workspace_tasks_filters_by_project_and_assignee(
    authenticated_client, workspace, user
):
    from tests.factories import UserFactory

    other = UserFactory(email="other@example.com")
    from workspaces.models import WorkspaceMember

    WorkspaceMember.objects.get_or_create(
        workspace=workspace, user=other, defaults={"role": WorkspaceMember.Role.EDITOR}
    )
    project_a = ProjectFactory(workspace=workspace, manager=user, name="Alpha")
    project_b = ProjectFactory(workspace=workspace, manager=user, name="Beta")
    root_a = project_a.wbs_nodes.get(code="1")
    root_b = project_b.wbs_nodes.get(code="1")
    node_a = WBSNode.objects.create(
        project=project_a,
        parent=root_a,
        title="Task A",
        code="1.1",
        node_type=WBSNode.NodeType.WORK_PACKAGE,
        position=0,
        assignee=user,
    )
    node_b = WBSNode.objects.create(
        project=project_b,
        parent=root_b,
        title="Task B",
        code="1.1",
        node_type=WBSNode.NodeType.WORK_PACKAGE,
        position=0,
        assignee=other,
    )
    ScheduleActivity.objects.create(wbs_node=node_a, progress=0)
    ScheduleActivity.objects.create(wbs_node=node_b, progress=0)

    all_resp = authenticated_client.get("/api/workspace/tasks/")
    assert all_resp.status_code == status.HTTP_200_OK
    ids = {row["wbs_id"] for row in all_resp.data["tasks"]}
    assert node_a.id in ids
    assert node_b.id in ids

    by_project = authenticated_client.get(
        f"/api/workspace/tasks/?project={project_a.id}"
    )
    assert by_project.status_code == status.HTTP_200_OK
    assert all(row["project_id"] == project_a.id for row in by_project.data["tasks"])

    by_user = authenticated_client.get(f"/api/workspace/tasks/?assignee={user.id}")
    assert by_user.status_code == status.HTTP_200_OK
    assert all(row["assignee_id"] == user.id for row in by_user.data["tasks"])


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
def test_delivery_my_tasks_includes_wbs(authenticated_client, workspace, user):
    from delivery.models import DeliverySettings

    DeliverySettings.objects.update_or_create(
        workspace=workspace, defaults={"agent_ops_enabled": True}
    )
    project = ProjectFactory(workspace=workspace, manager=user, name="WBS Inbox")
    root = project.wbs_nodes.get(code="1")
    node = WBSNode.objects.create(
        project=project,
        parent=root,
        title="Agent WBS task",
        description="Do the thing",
        code="1.2",
        node_type=WBSNode.NodeType.WORK_PACKAGE,
        position=0,
        assignee=user,
    )
    ScheduleActivity.objects.create(
        wbs_node=node,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=3),
        progress=0,
    )
    response = authenticated_client.get("/api/delivery/my-tasks/")
    assert response.status_code == status.HTTP_200_OK
    wbs_rows = response.data.get("wbs_tasks") or []
    assert any(row["wbs_id"] == node.id for row in wbs_rows)
    assert any(row["description"] == "Do the thing" for row in wbs_rows)
    assert response.data["total"] >= 1


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
