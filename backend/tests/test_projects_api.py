import pytest
from rest_framework import status

from kanban.models import Board, Card
from projects.models import ActivityDependency, Project, ScheduleActivity, WBSNode


@pytest.fixture
def project(workspace, user):
    return Project.objects.create(
        workspace=workspace,
        name="Website Redesign",
        description="PMBOK test project",
        manager=user,
    )


@pytest.mark.django_db
def test_create_project_creates_board_and_root_wbs(authenticated_client, workspace):
    response = authenticated_client.post(
        "/api/projects/",
        {"name": "New Project", "description": "Test", "status": "planning"},
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED
    project = Project.objects.get(name="New Project")
    assert project.workspace_id == workspace.id
    assert Board.objects.filter(project=project).exists()
    assert project.wbs_nodes.filter(parent__isnull=True, code="1").exists()


@pytest.mark.django_db
def test_list_projects(authenticated_client, project):
    response = authenticated_client.get("/api/projects/")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) >= 1
    assert response.data[0]["name"] == "Website Redesign"


@pytest.mark.django_db
def test_project_dashboard(authenticated_client, project):
    response = authenticated_client.get(f"/api/projects/{project.id}/dashboard/")
    assert response.status_code == status.HTTP_200_OK
    assert response.data["project_id"] == project.id
    assert "progress" in response.data


@pytest.mark.django_db
def test_wbs_tree_returns_root(authenticated_client, project):
    response = authenticated_client.get(f"/api/projects/{project.id}/wbs/")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 1
    assert response.data[0]["code"] == "1"


@pytest.mark.django_db
def test_create_wbs_work_package(authenticated_client, project):
    root = project.wbs_nodes.get(code="1")
    response = authenticated_client.post(
        f"/api/projects/{project.id}/wbs/",
        {
            "title": "Design mockups",
            "parent_id": root.id,
            "node_type": "work_package",
        },
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED
    node = WBSNode.objects.get(title="Design mockups")
    assert node.code == "1.1"
    assert ScheduleActivity.objects.filter(wbs_node=node).exists()
    assert Card.objects.filter(wbs_node=node).exists()


@pytest.mark.django_db
def test_schedule_endpoint(authenticated_client, project):
    root = project.wbs_nodes.get(code="1")
    authenticated_client.post(
        f"/api/projects/{project.id}/wbs/",
        {"title": "Task A", "parent_id": root.id, "node_type": "work_package"},
        format="json",
    )
    response = authenticated_client.get(f"/api/projects/{project.id}/schedule/")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data["activities"]) >= 1


@pytest.mark.django_db
def test_update_activity_progress_syncs_kanban(authenticated_client, project):
    root = project.wbs_nodes.get(code="1")
    authenticated_client.post(
        f"/api/projects/{project.id}/wbs/",
        {"title": "Task B", "parent_id": root.id, "node_type": "work_package"},
        format="json",
    )
    activity = ScheduleActivity.objects.get(wbs_node__title="Task B")
    card = Card.objects.get(wbs_node__title="Task B")
    todo_column = card.column.board.columns.get(position=0)
    done_column = card.column.board.columns.get(position=2)

    response = authenticated_client.patch(
        f"/api/activities/{activity.id}/",
        {"progress": 100},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    card.refresh_from_db()
    assert card.column_id == done_column.id
    assert card.column_id != todo_column.id


@pytest.mark.django_db
def test_create_activity_dependency(authenticated_client, project):
    root = project.wbs_nodes.get(code="1")
    for title in ("Task 1", "Task 2"):
        authenticated_client.post(
            f"/api/projects/{project.id}/wbs/",
            {"title": title, "parent_id": root.id, "node_type": "work_package"},
            format="json",
        )
    activities = list(
        ScheduleActivity.objects.filter(wbs_node__project=project).order_by("id")
    )
    response = authenticated_client.post(
        f"/api/projects/{project.id}/dependencies/",
        {
            "predecessor_id": activities[0].id,
            "successor_id": activities[1].id,
            "dependency_type": "FS",
            "lag_days": 0,
        },
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert ActivityDependency.objects.filter(
        predecessor=activities[0],
        successor=activities[1],
    ).exists()


@pytest.mark.django_db
def test_move_wbs_node_reparents_and_recalculates_codes(authenticated_client, project):
    root = project.wbs_nodes.get(code="1")
    for title in ("Alpha", "Beta"):
        authenticated_client.post(
            f"/api/projects/{project.id}/wbs/",
            {"title": title, "parent_id": root.id, "node_type": "work_package"},
            format="json",
        )
    alpha = WBSNode.objects.get(title="Alpha")
    beta = WBSNode.objects.get(title="Beta")

    response = authenticated_client.patch(
        f"/api/wbs/{alpha.id}/",
        {"parent_id": beta.id, "position": 0},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    alpha.refresh_from_db()
    assert alpha.parent_id == beta.id
    assert alpha.code == "1.1.1"


@pytest.mark.django_db
def test_move_wbs_node_reorders_siblings(authenticated_client, project):
    root = project.wbs_nodes.get(code="1")
    for title in ("First", "Second"):
        authenticated_client.post(
            f"/api/projects/{project.id}/wbs/",
            {"title": title, "parent_id": root.id, "node_type": "work_package"},
            format="json",
        )
    first = WBSNode.objects.get(title="First")
    second = WBSNode.objects.get(title="Second")

    response = authenticated_client.patch(
        f"/api/wbs/{first.id}/",
        {"parent_id": root.id, "position": 1},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    first.refresh_from_db()
    second.refresh_from_db()
    assert first.position == 1
    assert second.position == 0


@pytest.mark.django_db
def test_move_wbs_node_rejects_descendant_parent(authenticated_client, project):
    root = project.wbs_nodes.get(code="1")
    authenticated_client.post(
        f"/api/projects/{project.id}/wbs/",
        {"title": "Parent task", "parent_id": root.id, "node_type": "work_package"},
        format="json",
    )
    parent = WBSNode.objects.get(title="Parent task")
    authenticated_client.post(
        f"/api/projects/{project.id}/wbs/",
        {"title": "Child task", "parent_id": parent.id, "node_type": "work_package"},
        format="json",
    )
    child = WBSNode.objects.get(title="Child task")

    response = authenticated_client.patch(
        f"/api/wbs/{parent.id}/",
        {"parent_id": child.id, "position": 0},
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_delete_wbs_node(authenticated_client, project):
    root = project.wbs_nodes.get(code="1")
    create = authenticated_client.post(
        f"/api/projects/{project.id}/wbs/",
        {"title": "Temp", "parent_id": root.id},
        format="json",
    )
    node = WBSNode.objects.get(title="Temp")
    response = authenticated_client.delete(f"/api/wbs/{node.id}/")
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not WBSNode.objects.filter(pk=node.id).exists()
