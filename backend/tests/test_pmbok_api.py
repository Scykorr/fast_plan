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
