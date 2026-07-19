import pytest
from rest_framework import status

from kanban.models import Card
from projects.models import Project, WBSNode
from tests.factories import ProjectFactory


@pytest.mark.django_db
def test_project_template_copies_wbs_and_board(authenticated_client, workspace, user):
    source = ProjectFactory(workspace=workspace, manager=user, name="Source")
    root = source.wbs_nodes.get(parent__isnull=True)
    WBSNode.objects.create(
        project=source,
        parent=root,
        code="1.1",
        title="Discovery",
        node_type=WBSNode.NodeType.WORK_PACKAGE,
        position=0,
    )
    source.board.columns.filter(position=0).update(title="Backlog")

    template = authenticated_client.post(
        "/api/project-templates/",
        {
            "name": "Delivery template",
            "source_project_id": source.id,
        },
        format="json",
    )
    assert template.status_code == status.HTTP_201_CREATED

    created = authenticated_client.post(
        "/api/projects/",
        {
            "name": "New delivery",
            "status": "planning",
            "template_id": template.data["id"],
        },
        format="json",
    )
    assert created.status_code == status.HTTP_201_CREATED
    project = Project.objects.get(pk=created.data["id"])
    assert project.wbs_nodes.filter(title="Discovery").exists()
    assert list(project.board.columns.values_list("title", flat=True))[0] == "Backlog"


@pytest.mark.django_db
def test_board_analytics_tracks_completed_card(authenticated_client, workspace, user):
    project = ProjectFactory(workspace=workspace, manager=user)
    columns = list(project.board.columns.order_by("position"))
    card = Card.objects.create(column=columns[0], title="Ship feature", position=0)

    moved = authenticated_client.post(
        f"/api/cards/{card.id}/move/",
        {"column_id": columns[-1].id, "position": 0},
        format="json",
    )
    assert moved.status_code == status.HTTP_200_OK

    analytics = authenticated_client.get(
        f"/api/boards/{project.board.id}/analytics/?days=14"
    )
    assert analytics.status_code == status.HTTP_200_OK
    assert len(analytics.data["burndown"]) == 14
    assert analytics.data["burndown"][-1]["remaining"] == 0
    assert analytics.data["velocity"][-1]["completed"] == 1
