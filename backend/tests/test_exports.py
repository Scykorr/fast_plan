import pytest
from datetime import date
from rest_framework import status

from finance.models import Transaction
from projects.models import Project


@pytest.fixture
def project(workspace, user):
    return Project.objects.create(
        workspace=workspace,
        name="Export Project",
        manager=user,
        budget=1000,
        end_date=date(2026, 12, 31),
    )


@pytest.mark.django_db
def test_project_export_csv(authenticated_client, project):
    response = authenticated_client.get(f"/api/projects/{project.id}/export/?output=csv")
    assert response.status_code == status.HTTP_200_OK
    assert response["Content-Type"].startswith("text/csv")
    content = response.content.decode("utf-8")
    assert "code" in content.splitlines()[0]


@pytest.mark.django_db
def test_project_export_xlsx(authenticated_client, project):
    response = authenticated_client.get(f"/api/projects/{project.id}/export/?output=xlsx")
    assert response.status_code == status.HTTP_200_OK
    assert "spreadsheetml" in response["Content-Type"]
    assert len(response.content) > 0


@pytest.mark.django_db
def test_project_export_json_default(authenticated_client, project):
    response = authenticated_client.get(f"/api/projects/{project.id}/export/")
    assert response.status_code == status.HTTP_200_OK
    assert response.data["project"]["id"] == project.id


@pytest.mark.django_db
def test_project_milestones_ics(authenticated_client, project):
    response = authenticated_client.get(f"/api/projects/{project.id}/milestones.ics")
    assert response.status_code == status.HTTP_200_OK
    assert response["Content-Type"].startswith("text/calendar")
    body = response.content.decode("utf-8")
    assert "BEGIN:VCALENDAR" in body
    assert "Дедлайн проекта" in body


@pytest.mark.django_db
def test_workspace_calendar_ics(authenticated_client, project):
    response = authenticated_client.get("/api/workspace/calendar.ics")
    assert response.status_code == status.HTTP_200_OK
    assert response["Content-Type"].startswith("text/calendar")
    assert "BEGIN:VCALENDAR" in response.content.decode("utf-8")


@pytest.mark.django_db
def test_transactions_export_csv(authenticated_client, project):
    Transaction.objects.create(
        workspace=project.workspace,
        project=project,
        title="License",
        amount=500,
        transaction_type="expense",
        transaction_date=date.today(),
    )
    response = authenticated_client.get("/api/finance/transactions/export/?format=csv")
    assert response.status_code == status.HTTP_200_OK
    assert response["Content-Type"].startswith("text/csv")
    content = response.content.decode("utf-8")
    assert "License" in content


@pytest.mark.django_db
def test_transactions_export_xlsx(authenticated_client, project):
    Transaction.objects.create(
        workspace=project.workspace,
        project=project,
        title="License",
        amount=500,
        transaction_type="expense",
        transaction_date=date.today(),
    )
    response = authenticated_client.get("/api/finance/transactions/export/?format=xlsx")
    assert response.status_code == status.HTTP_200_OK
    assert "spreadsheetml" in response["Content-Type"]
