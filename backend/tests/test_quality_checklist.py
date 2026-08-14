import pytest
from rest_framework import status

from tests.factories import ProjectFactory
from projects.models import WBSQualityCheckItem


@pytest.fixture
def project(workspace, user):
    return ProjectFactory(workspace=workspace, manager=user)


@pytest.mark.django_db
def test_quality_check_crud(authenticated_client, project):
    root = project.wbs_nodes.get(code="1")
    created = authenticated_client.post(
        f"/api/projects/{project.id}/wbs/",
        {"title": "WP", "parent_id": root.id, "node_type": "work_package"},
        format="json",
    )
    assert created.status_code == status.HTTP_201_CREATED

    def flatten(nodes):
        out = []
        for node in nodes:
            out.append(node)
            out.extend(flatten(node.get("children") or []))
        return out

    node_id = next(n["id"] for n in flatten(created.data) if n.get("title") == "WP")
    listed_empty = authenticated_client.get(f"/api/wbs/{node_id}/quality-checks/")
    assert listed_empty.status_code == status.HTTP_200_OK
    assert listed_empty.data == []

    item = authenticated_client.post(
        f"/api/wbs/{node_id}/quality-checks/",
        {
            "title": "Unit tests green",
            "evidence_url": "https://example.com/ci",
        },
        format="json",
    )
    assert item.status_code == status.HTTP_201_CREATED
    assert item.data["result"] == WBSQualityCheckItem.Result.OPEN
    item_id = item.data["id"]

    patched = authenticated_client.patch(
        f"/api/quality-checks/{item_id}/",
        {"result": "pass"},
        format="json",
    )
    assert patched.status_code == status.HTTP_200_OK
    assert patched.data["result"] == "pass"
    assert patched.data["checked_by"] is not None

    tree = authenticated_client.get(f"/api/projects/{project.id}/wbs/")
    node = next(n for n in flatten(tree.data) if n["id"] == node_id)
    assert node["quality"]["total"] == 1
    assert node["quality"]["passed"] == 1
    assert node["quality"]["failed"] == 0

    deleted = authenticated_client.delete(f"/api/quality-checks/{item_id}/")
    assert deleted.status_code == status.HTTP_204_NO_CONTENT
    assert not WBSQualityCheckItem.objects.filter(pk=item_id).exists()


@pytest.mark.django_db
def test_quality_check_rejects_bad_result(authenticated_client, project):
    root = project.wbs_nodes.get(code="1")
    created = authenticated_client.post(
        f"/api/projects/{project.id}/wbs/",
        {"title": "WP2", "parent_id": root.id},
        format="json",
    )

    def flatten(nodes):
        out = []
        for node in nodes:
            out.append(node)
            out.extend(flatten(node.get("children") or []))
        return out

    node_id = next(n["id"] for n in flatten(created.data) if n.get("title") == "WP2")
    response = authenticated_client.post(
        f"/api/wbs/{node_id}/quality-checks/",
        {"title": "Check", "result": "maybe"},
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
