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
    assert "results" in response.data
    assert "count" in response.data
    assert len(response.data["results"]) >= 1


@pytest.mark.django_db
def test_notifications_pagination(authenticated_client, user, workspace):
    for i in range(25):
        Notification.objects.create(
            user=user,
            workspace=workspace,
            notification_type="deadline",
            title=f"Test {i}",
        )
    first_page = authenticated_client.get("/api/notifications/")
    assert first_page.status_code == status.HTTP_200_OK
    assert first_page.data["count"] == 25
    assert len(first_page.data["results"]) == 20
    assert first_page.data["next"] is not None

    second_page = authenticated_client.get("/api/notifications/?page=2")
    assert second_page.status_code == status.HTTP_200_OK
    assert len(second_page.data["results"]) == 5
    assert second_page.data["next"] is None


@pytest.mark.django_db
def test_mark_all_read(authenticated_client, user, workspace, other_user):
    for i in range(3):
        Notification.objects.create(
            user=user,
            workspace=workspace,
            notification_type="deadline",
            title=f"Test {i}",
        )
    Notification.objects.create(
        user=other_user,
        workspace=workspace,
        notification_type="deadline",
        title="Someone else's",
    )
    response = authenticated_client.post("/api/notifications/mark-all-read/")
    assert response.status_code == status.HTTP_200_OK
    assert response.data["updated"] == 3
    assert not Notification.objects.filter(user=user, is_read=False).exists()
    assert Notification.objects.filter(user=other_user, is_read=False).exists()


@pytest.mark.django_db
def test_mark_all_read_scoped_to_workspace(authenticated_client, user, workspace):
    from workspaces.models import Workspace

    other_workspace = Workspace.objects.create(name="Other WS", owner=user)
    Notification.objects.create(
        user=user,
        workspace=workspace,
        notification_type="deadline",
        title="In workspace",
    )
    Notification.objects.create(
        user=user,
        workspace=other_workspace,
        notification_type="deadline",
        title="Other workspace",
    )
    response = authenticated_client.post(
        "/api/notifications/mark-all-read/",
        HTTP_X_WORKSPACE_ID=str(workspace.id),
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.data["updated"] == 1
    assert Notification.objects.filter(
        user=user, workspace=other_workspace, is_read=False
    ).exists()


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
