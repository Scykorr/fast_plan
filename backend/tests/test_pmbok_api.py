import pytest
from datetime import date
from rest_framework import status

from projects.models import ProjectBaseline, RACIEntry, Risk, Stakeholder


@pytest.fixture
def project(workspace, user):
    return __import__("projects.models", fromlist=["Project"]).Project.objects.create(
        workspace=workspace,
        name="PMBOK Project",
        manager=user,
        budget=100000,
    )


@pytest.mark.django_db
def test_create_risk(authenticated_client, project):
    response = authenticated_client.post(
        f"/api/projects/{project.id}/risks/",
        {
            "title": "Scope creep",
            "probability": 4,
            "impact": 5,
            "status": "open",
        },
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["score"] == 20
    assert Risk.objects.filter(project=project).count() == 1


@pytest.mark.django_db
def test_update_and_delete_risk(authenticated_client, project):
    risk = Risk.objects.create(
        project=project, title="Vendor delay", probability=2, impact=2
    )
    response = authenticated_client.patch(
        f"/api/risks/{risk.id}/",
        {
            "description": "Vendor may miss deadline",
            "status": "mitigated",
            "mitigation": "Add buffer",
            "probability": 4,
            "impact": 3,
        },
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.data["status"] == "mitigated"
    assert response.data["mitigation"] == "Add buffer"
    assert response.data["score"] == 12
    risk.refresh_from_db()
    assert risk.description == "Vendor may miss deadline"

    delete = authenticated_client.delete(f"/api/risks/{risk.id}/")
    assert delete.status_code == status.HTTP_204_NO_CONTENT
    assert not Risk.objects.filter(pk=risk.id).exists()


@pytest.mark.django_db
def test_create_stakeholder_and_raci(authenticated_client, project):
    root = project.wbs_nodes.get(code="1")
    stakeholder = Stakeholder.objects.create(
        project=project, name="Alice", role="Sponsor"
    )
    response = authenticated_client.post(
        f"/api/projects/{project.id}/raci/",
        {
            "wbs_node_id": root.id,
            "stakeholder_id": stakeholder.id,
            "raci_type": "A",
        },
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert RACIEntry.objects.filter(wbs_node=root, stakeholder=stakeholder).exists()


@pytest.mark.django_db
def test_update_and_delete_stakeholder(authenticated_client, project):
    stakeholder = Stakeholder.objects.create(project=project, name="Eve", role="QA")
    response = authenticated_client.patch(
        f"/api/stakeholders/{stakeholder.id}/",
        {
            "role": "Sponsor",
            "interest": 5,
            "influence": 4,
            "contact_email": "eve@example.com",
            "notes": "Key decision maker",
        },
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.data["role"] == "Sponsor"
    assert response.data["contact_email"] == "eve@example.com"
    stakeholder.refresh_from_db()
    assert stakeholder.notes == "Key decision maker"

    delete = authenticated_client.delete(f"/api/stakeholders/{stakeholder.id}/")
    assert delete.status_code == status.HTTP_204_NO_CONTENT
    assert not Stakeholder.objects.filter(pk=stakeholder.id).exists()


@pytest.mark.django_db
def test_raci_upsert_and_delete(authenticated_client, project):
    root = project.wbs_nodes.get(code="1")
    stakeholder = Stakeholder.objects.create(
        project=project, name="Bob", role="PM"
    )
    first = authenticated_client.post(
        f"/api/projects/{project.id}/raci/",
        {
            "wbs_node_id": root.id,
            "stakeholder_id": stakeholder.id,
            "raci_type": "R",
        },
        format="json",
    )
    assert first.status_code == status.HTTP_201_CREATED
    second = authenticated_client.post(
        f"/api/projects/{project.id}/raci/",
        {
            "wbs_node_id": root.id,
            "stakeholder_id": stakeholder.id,
            "raci_type": "A",
        },
        format="json",
    )
    assert second.status_code == status.HTTP_200_OK
    assert second.data["raci_type"] == "A"
    assert RACIEntry.objects.filter(wbs_node=root, stakeholder=stakeholder).count() == 1

    delete = authenticated_client.delete(f"/api/raci/{first.data['id']}/")
    assert delete.status_code == status.HTTP_204_NO_CONTENT
    assert not RACIEntry.objects.filter(pk=first.data["id"]).exists()


@pytest.mark.django_db
def test_raci_invalid_type_and_cross_project(authenticated_client, project, workspace, user):
    from projects.models import Project

    root = project.wbs_nodes.get(code="1")
    stakeholder = Stakeholder.objects.create(project=project, name="Carol", role="QA")
    bad_type = authenticated_client.post(
        f"/api/projects/{project.id}/raci/",
        {
            "wbs_node_id": root.id,
            "stakeholder_id": stakeholder.id,
            "raci_type": "X",
        },
        format="json",
    )
    assert bad_type.status_code == status.HTTP_400_BAD_REQUEST

    other = Project.objects.create(workspace=workspace, name="Other", manager=user)
    other_root = other.wbs_nodes.get(code="1")
    cross = authenticated_client.post(
        f"/api/projects/{project.id}/raci/",
        {
            "wbs_node_id": other_root.id,
            "stakeholder_id": stakeholder.id,
            "raci_type": "R",
        },
        format="json",
    )
    assert cross.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_raci_viewer_cannot_mutate(api_client, project, workspace, user, other_user):
    from workspaces.models import WorkspaceMember

    WorkspaceMember.objects.create(
        workspace=workspace,
        user=other_user,
        role=WorkspaceMember.Role.VIEWER,
    )
    other_user.active_workspace = workspace
    other_user.save(update_fields=["active_workspace"])
    root = project.wbs_nodes.get(code="1")
    stakeholder = Stakeholder.objects.create(project=project, name="Dan", role="Dev")
    api_client.force_authenticate(user=other_user)
    api_client.credentials(HTTP_X_WORKSPACE_ID=str(workspace.id))
    listed = api_client.get(f"/api/projects/{project.id}/raci/")
    assert listed.status_code == status.HTTP_200_OK
    created = api_client.post(
        f"/api/projects/{project.id}/raci/",
        {
            "wbs_node_id": root.id,
            "stakeholder_id": stakeholder.id,
            "raci_type": "I",
        },
        format="json",
    )
    assert created.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_charter_get_and_patch(authenticated_client, project):
    response = authenticated_client.get(f"/api/projects/{project.id}/charter/")
    assert response.status_code == status.HTTP_200_OK
    patch = authenticated_client.patch(
        f"/api/projects/{project.id}/charter/",
        {"goals": "Launch MVP"},
        format="json",
    )
    assert patch.status_code == status.HTTP_200_OK
    assert patch.data["goals"] == "Launch MVP"


@pytest.mark.django_db
def test_create_baseline(authenticated_client, project):
    root = project.wbs_nodes.get(code="1")
    authenticated_client.post(
        f"/api/projects/{project.id}/wbs/",
        {"title": "Task", "parent_id": root.id, "node_type": "work_package"},
        format="json",
    )
    response = authenticated_client.post(
        f"/api/projects/{project.id}/baselines/",
        {"name": "Baseline 1"},
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert ProjectBaseline.objects.filter(project=project).count() == 1
    assert len(response.data["activities"]) >= 1


@pytest.mark.django_db
def test_update_and_delete_baseline(authenticated_client, project):
    root = project.wbs_nodes.get(code="1")
    authenticated_client.post(
        f"/api/projects/{project.id}/wbs/",
        {"title": "Task", "parent_id": root.id, "node_type": "work_package"},
        format="json",
    )
    created = authenticated_client.post(
        f"/api/projects/{project.id}/baselines/",
        {"name": "Baseline 1"},
        format="json",
    )
    baseline_id = created.data["id"]

    renamed = authenticated_client.patch(
        f"/api/baselines/{baseline_id}/",
        {"name": "Baseline v2"},
        format="json",
    )
    assert renamed.status_code == status.HTTP_200_OK
    assert renamed.data["name"] == "Baseline v2"

    blank = authenticated_client.patch(
        f"/api/baselines/{baseline_id}/",
        {"name": "   "},
        format="json",
    )
    assert blank.status_code == status.HTTP_400_BAD_REQUEST

    deleted = authenticated_client.delete(f"/api/baselines/{baseline_id}/")
    assert deleted.status_code == status.HTTP_204_NO_CONTENT
    assert not ProjectBaseline.objects.filter(pk=baseline_id).exists()


@pytest.mark.django_db
def test_critical_path(authenticated_client, project):
    root = project.wbs_nodes.get(code="1")
    for title in ("A", "B"):
        authenticated_client.post(
            f"/api/projects/{project.id}/wbs/",
            {"title": title, "parent_id": root.id, "node_type": "work_package"},
            format="json",
        )
    from projects.models import ScheduleActivity

    activities = list(ScheduleActivity.objects.filter(wbs_node__project=project).order_by("id"))
    authenticated_client.post(
        f"/api/projects/{project.id}/dependencies/",
        {
            "predecessor_id": activities[0].id,
            "successor_id": activities[1].id,
            "dependency_type": "FS",
        },
        format="json",
    )
    response = authenticated_client.get(f"/api/projects/{project.id}/critical-path/")
    assert response.status_code == status.HTTP_200_OK
    assert "critical_path_ids" in response.data


@pytest.mark.django_db
def test_project_export(authenticated_client, project):
    response = authenticated_client.get(f"/api/projects/{project.id}/export/")
    assert response.status_code == status.HTTP_200_OK
    assert response.data["project"]["id"] == project.id
    assert "charter" in response.data


@pytest.mark.django_db
def test_enhanced_dashboard(authenticated_client, project):
    response = authenticated_client.get(f"/api/projects/{project.id}/dashboard/")
    assert response.status_code == status.HTTP_200_OK
    assert "evm" in response.data
    assert "top_risks" in response.data
    assert "critical_path" in response.data
