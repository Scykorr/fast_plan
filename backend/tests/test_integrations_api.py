import pytest
from rest_framework import status
from rest_framework.test import APIClient

from tests.factories import ProjectFactory
from projects.models import Project
from workspaces.models import WebhookDelivery, WorkspaceAPIToken


@pytest.fixture
def project(workspace, user):
    return ProjectFactory(workspace=workspace, manager=user)


@pytest.mark.django_db
def test_workspace_api_token_is_returned_once_and_scoped(
    authenticated_client,
    workspace,
):
    created = authenticated_client.post(
        "/api/workspace/api-tokens/",
        {"name": "Reporting", "scopes": ["read"]},
        format="json",
    )
    assert created.status_code == status.HTTP_201_CREATED
    raw_token = created.data["token"]
    assert raw_token.startswith("fp_")

    listed = authenticated_client.get("/api/workspace/api-tokens/")
    assert listed.status_code == status.HTTP_200_OK
    assert "token" not in listed.data[0]

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {raw_token}")
    projects = client.get("/api/projects/")
    assert projects.status_code == status.HTTP_200_OK

    denied = client.post(
        "/api/projects/",
        {"name": "Cannot write"},
        format="json",
    )
    assert denied.status_code == status.HTTP_403_FORBIDDEN

    token_id = created.data["id"]
    revoked = authenticated_client.delete(f"/api/workspace/api-tokens/{token_id}/")
    assert revoked.status_code == status.HTTP_204_NO_CONTENT
    assert WorkspaceAPIToken.objects.get(pk=token_id).revoked_at is not None
    assert client.get("/api/projects/").status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_write_api_token_is_locked_to_its_workspace(authenticated_client, workspace):
    created = authenticated_client.post(
        "/api/workspace/api-tokens/",
        {"name": "Automation", "scopes": ["read", "write"]},
        format="json",
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {created.data['token']}")
    response = client.post(
        "/api/projects/",
        {"name": "Created by automation", "status": "planning"},
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert Project.objects.get(pk=response.data["id"]).workspace == workspace


@pytest.mark.django_db
def test_webhook_configuration_and_risk_event(
    authenticated_client,
    workspace,
    project,
):
    created = authenticated_client.post(
        "/api/workspace/webhooks/",
        {
            "name": "Risk receiver",
            "url": "https://hooks.example.com/fast-plan",
            "events": ["risk.created", "risk.updated"],
        },
        format="json",
    )
    assert created.status_code == status.HTTP_201_CREATED
    assert created.data["secret"]

    listed = authenticated_client.get("/api/workspace/webhooks/")
    assert listed.status_code == status.HTTP_200_OK
    assert "secret" not in listed.data[0]

    risk = authenticated_client.post(
        f"/api/projects/{project.id}/risks/",
        {
            "title": "Supplier delay",
            "probability": 4,
            "impact": 5,
            "status": "open",
        },
        format="json",
    )
    assert risk.status_code == status.HTTP_201_CREATED
    delivery = WebhookDelivery.objects.get(event="risk.created")
    assert delivery.endpoint.workspace == workspace
    assert delivery.payload["risk_id"] == risk.data["id"]


@pytest.mark.django_db
def test_webhook_rejects_non_https_url(authenticated_client):
    response = authenticated_client.post(
        "/api/workspace/webhooks/",
        {
            "name": "Unsafe",
            "url": "http://127.0.0.1/hook",
            "events": ["risk.created"],
        },
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
