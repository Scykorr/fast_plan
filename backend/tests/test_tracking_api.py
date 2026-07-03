import pytest
from rest_framework import status

from projects.models import Project, WBSNode
from tracking.models import CustomField, IssueStatus, Tracker


@pytest.fixture
def project(workspace, user):
    return Project.objects.create(
        workspace=workspace,
        name="Tracker Test Project",
        description="Test",
        manager=user,
    )


@pytest.mark.django_db
def test_tracking_metadata_seeds_defaults(authenticated_client, workspace):
    response = authenticated_client.get("/api/tracking/metadata/")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data["trackers"]) >= 2
    assert len(response.data["statuses"]) >= 4
    assert Tracker.objects.filter(workspace=workspace).exists()
    assert IssueStatus.objects.filter(workspace=workspace).exists()


@pytest.mark.django_db
def test_create_tracker(authenticated_client, workspace):
    response = authenticated_client.post(
        "/api/tracking/trackers/",
        {"name": "Баг", "target": "issue", "position": 10},
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert Tracker.objects.filter(workspace=workspace, name="Баг").exists()


@pytest.mark.django_db
def test_create_custom_field_with_trackers(authenticated_client, workspace):
    tracker = Tracker.objects.filter(workspace=workspace, target="issue").first()
    response = authenticated_client.post(
        "/api/tracking/custom-fields/",
        {
            "name": "Компонент",
            "field_format": "list",
            "tracker_ids": [tracker.id],
            "enumerations": [
                {"name": "Backend", "position": 0},
                {"name": "Frontend", "position": 1},
            ],
        },
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED
    field = CustomField.objects.get(name="Компонент")
    assert field.enumerations.count() == 2
    assert field.trackers.filter(pk=tracker.id).exists()


@pytest.mark.django_db
def test_create_link_list_custom_field(authenticated_client, workspace):
    tracker = Tracker.objects.filter(workspace=workspace, target="issue").first()
    response = authenticated_client.post(
        "/api/tracking/custom-fields/",
        {
            "name": "Регион",
            "field_format": "link_list",
            "tracker_ids": [tracker.id],
            "enumerations": [
                {"name": "Европа", "position": 0, "parent_id": None},
            ],
        },
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED
    field = CustomField.objects.get(name="Регион")
    parent = field.enumerations.get(name="Европа", parent__isnull=True)

    response = authenticated_client.patch(
        f"/api/tracking/custom-fields/{field.id}/",
        {
            "enumerations": [
                {"id": parent.id, "name": "Европа", "position": 0, "parent_id": None},
                {
                    "name": "Германия",
                    "position": 0,
                    "parent_id": parent.id,
                },
            ],
        },
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    europe = field.enumerations.get(name="Европа", parent__isnull=True)
    assert field.enumerations.filter(parent_id=europe.id, name="Германия").exists()


@pytest.mark.django_db
def test_update_wbs_node_with_tracker_and_custom_values(
    authenticated_client, project, workspace
):
    seed_response = authenticated_client.get("/api/tracking/metadata/")
    tracker = Tracker.objects.filter(workspace=workspace, target="issue").first()
    status_obj = IssueStatus.objects.filter(workspace=workspace).first()
    priority_field = next(
        item for item in seed_response.data["custom_fields"] if item["name"] == "Приоритет"
    )
    root = project.wbs_nodes.get(code="1")
    authenticated_client.post(
        f"/api/projects/{project.id}/wbs/",
        {"title": "Dev task", "parent_id": root.id, "node_type": "work_package"},
        format="json",
    )
    node = WBSNode.objects.get(title="Dev task")
    response = authenticated_client.patch(
        f"/api/wbs/{node.id}/",
        {
            "tracker_id": tracker.id,
            "workflow_status_id": status_obj.id,
            "custom_values": {str(priority_field["id"]): "Высокий"},
        },
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    node.refresh_from_db()
    assert node.tracker_id == tracker.id
    assert node.workflow_status_id == status_obj.id

    tree = response.data
    flat = []
    stack = list(tree)
    while stack:
        item = stack.pop()
        flat.append(item)
        stack.extend(item.get("children", []))
    updated = next(item for item in flat if item["id"] == node.id)
    assert updated["custom_values"]
