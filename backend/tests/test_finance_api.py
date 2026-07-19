import pytest
from datetime import date
from rest_framework import status

from finance.models import Transaction
from projects.models import Project


@pytest.fixture
def project(workspace, user):
    return Project.objects.create(
        workspace=workspace,
        name="Finance Project",
        manager=user,
        budget=50000,
    )


@pytest.mark.django_db
def test_create_transaction(authenticated_client, project):
    response = authenticated_client.post(
        "/api/finance/transactions/",
        {
            "project_id": project.id,
            "title": "Hosting",
            "amount": "1200.00",
            "transaction_type": "expense",
            "transaction_date": date.today().isoformat(),
        },
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert Transaction.objects.filter(project=project).count() == 1


@pytest.mark.django_db
def test_update_and_delete_transaction(authenticated_client, project):
    created = authenticated_client.post(
        "/api/finance/transactions/",
        {
            "project_id": project.id,
            "title": "Hosting",
            "amount": "1200.00",
            "transaction_type": "expense",
            "transaction_date": date.today().isoformat(),
            "category": "infra",
        },
        format="json",
    )
    assert created.status_code == status.HTTP_201_CREATED
    tx_id = created.data["id"]

    updated = authenticated_client.patch(
        f"/api/finance/transactions/{tx_id}/",
        {
            "title": "Hosting Pro",
            "amount": "1500.00",
            "transaction_type": "expense",
            "transaction_date": date.today().isoformat(),
            "category": "infra",
            "project_id": project.id,
        },
        format="json",
    )
    assert updated.status_code == status.HTTP_200_OK
    assert updated.data["title"] == "Hosting Pro"
    assert updated.data["amount"] == "1500.00"

    deleted = authenticated_client.delete(f"/api/finance/transactions/{tx_id}/")
    assert deleted.status_code == status.HTTP_204_NO_CONTENT
    assert not Transaction.objects.filter(pk=tx_id).exists()


@pytest.mark.django_db
def test_project_finance_summary(authenticated_client, project):
    Transaction.objects.create(
        workspace=project.workspace,
        project=project,
        title="License",
        amount=500,
        transaction_type="expense",
        transaction_date=date.today(),
    )
    response = authenticated_client.get(f"/api/projects/{project.id}/finance/")
    assert response.status_code == status.HTTP_200_OK
    assert response.data["budget"] == 50000
    assert response.data["actual_expenses"] == 500
