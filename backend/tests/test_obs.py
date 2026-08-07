import pytest
from rest_framework import status

from tests.factories import ProjectFactory
from workspaces.models import ObsRole, OrgUnit


@pytest.fixture
def project(workspace, user):
    return ProjectFactory(workspace=workspace, manager=user)


@pytest.mark.django_db
def test_org_unit_tree_and_flat(authenticated_client, workspace):
    root = authenticated_client.post(
        "/api/workspace/org-units/",
        {"name": "Engineering", "code": "ENG"},
        format="json",
    )
    assert root.status_code == status.HTTP_201_CREATED
    child = authenticated_client.post(
        "/api/workspace/org-units/",
        {"name": "Backend", "parent_id": root.data["id"]},
        format="json",
    )
    assert child.status_code == status.HTTP_201_CREATED

    tree = authenticated_client.get("/api/workspace/org-units/")
    assert tree.status_code == status.HTTP_200_OK
    assert len(tree.data) == 1
    assert tree.data[0]["name"] == "Engineering"
    assert len(tree.data[0]["children"]) == 1
    assert tree.data[0]["children"][0]["name"] == "Backend"

    flat = authenticated_client.get("/api/workspace/org-units/?flat=1")
    assert flat.status_code == status.HTTP_200_OK
    assert len(flat.data) == 2
    assert "children" not in flat.data[0]


@pytest.mark.django_db
def test_obs_role_crud(authenticated_client, workspace):
    created = authenticated_client.post(
        "/api/workspace/obs-roles/",
        {"name": "Tech Lead", "code": "TL"},
        format="json",
    )
    assert created.status_code == status.HTTP_201_CREATED
    role_id = created.data["id"]

    listed = authenticated_client.get("/api/workspace/obs-roles/")
    assert listed.status_code == status.HTTP_200_OK
    assert any(row["id"] == role_id for row in listed.data)

    patched = authenticated_client.patch(
        f"/api/obs-roles/{role_id}/",
        {"name": "Lead Engineer"},
        format="json",
    )
    assert patched.status_code == status.HTTP_200_OK
    assert patched.data["name"] == "Lead Engineer"

    deleted = authenticated_client.delete(f"/api/obs-roles/{role_id}/")
    assert deleted.status_code == status.HTTP_204_NO_CONTENT
    assert not ObsRole.objects.filter(pk=role_id).exists()


@pytest.mark.django_db
def test_wbs_patch_obs_fields(authenticated_client, project, workspace):
    unit = OrgUnit.objects.create(workspace=workspace, name="QA", code="QA")
    role = ObsRole.objects.create(workspace=workspace, name="Tester", code="QA")
    root = project.wbs_nodes.get(code="1")
    create = authenticated_client.post(
        f"/api/projects/{project.id}/wbs/",
        {"title": "Test package", "parent_id": root.id, "node_type": "work_package"},
        format="json",
    )
    assert create.status_code == status.HTTP_201_CREATED
    node_id = next(
        n["id"]
        for n in _flatten(create.data)
        if n.get("title") == "Test package"
    )

    response = authenticated_client.patch(
        f"/api/wbs/{node_id}/",
        {"org_unit_id": unit.id, "obs_role_id": role.id},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    updated = next(n for n in _flatten(response.data) if n["id"] == node_id)
    assert updated["org_unit_id"] == unit.id
    assert updated["org_unit_name"] == "QA"
    assert updated["obs_role_id"] == role.id
    assert updated["obs_role_name"] == "Tester"

    cleared = authenticated_client.patch(
        f"/api/wbs/{node_id}/",
        {"org_unit_id": None, "obs_role_id": None},
        format="json",
    )
    assert cleared.status_code == status.HTTP_200_OK
    cleared_node = next(n for n in _flatten(cleared.data) if n["id"] == node_id)
    assert cleared_node["org_unit_id"] is None
    assert cleared_node["obs_role_id"] is None


@pytest.mark.django_db
def test_wbs_rejects_foreign_org_unit(authenticated_client, project, other_user):
    other_ws = other_user.workspace_memberships.first().workspace
    foreign = OrgUnit.objects.create(workspace=other_ws, name="Foreign")
    root = project.wbs_nodes.get(code="1")
    create = authenticated_client.post(
        f"/api/projects/{project.id}/wbs/",
        {"title": "Pkg", "parent_id": root.id},
        format="json",
    )
    node_id = next(n["id"] for n in _flatten(create.data) if n.get("title") == "Pkg")

    response = authenticated_client.patch(
        f"/api/wbs/{node_id}/",
        {"org_unit_id": foreign.id},
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def _flatten(nodes):
    out = []
    for node in nodes:
        out.append(node)
        out.extend(_flatten(node.get("children") or []))
    return out
