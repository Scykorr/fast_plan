import pytest
from rest_framework import status

from notifications.models import Notification
from projects.models import Risk


@pytest.fixture
def project(workspace, user):
    from projects.models import Project

    return Project.objects.create(workspace=workspace, name="Notify Project", manager=user)


@pytest.mark.django_db
def test_list_notifications(authenticated_client, user, workspace):
    Notification.objects.create(
        user=user,
        workspace=workspace,
        notification_type="deadline",
        title="Test",
        message="Hello",
    )
    response = authenticated_client.get("/api/notifications/")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) >= 1


@pytest.mark.django_db
def test_high_risk_creates_notification(authenticated_client, project, user):
    authenticated_client.post(
        f"/api/projects/{project.id}/risks/",
        {
            "title": "Critical risk",
            "probability": 5,
            "impact": 5,
        },
        format="json",
    )
    assert Notification.objects.filter(
        user=user, notification_type=Notification.NotificationType.RISK
    ).exists()
