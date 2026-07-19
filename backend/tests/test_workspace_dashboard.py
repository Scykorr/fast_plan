from datetime import date, timedelta

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from finance.models import Transaction
from notifications.models import Notification
from projects.models import Risk, ScheduleActivity
from tests.factories import ProjectFactory, UserFactory, WorkspaceMemberFactory
from workspaces.models import WorkspaceMember
from workspaces.services import set_active_workspace


@pytest.fixture
def active_project(workspace, user):
    return ProjectFactory(workspace=workspace, manager=user, budget=1000, status="active")


@pytest.mark.django_db
def test_workspace_dashboard_overdue_and_risks(
    authenticated_client, workspace, user, active_project
):
    from projects.models import WBSNode

    root = active_project.wbs_nodes.filter(parent__isnull=True).first()
    node = WBSNode.objects.create(
        project=active_project,
        parent=root,
        title="Late task",
        code="1.1",
        node_type=WBSNode.NodeType.WORK_PACKAGE,
        position=0,
    )
    ScheduleActivity.objects.create(
        wbs_node=node,
        start_date=date.today() - timedelta(days=10),
        end_date=date.today() - timedelta(days=2),
        progress=40,
    )
    Risk.objects.create(
        project=active_project,
        title="Big risk",
        probability=5,
        impact=5,
        status=Risk.Status.OPEN,
    )
    Risk.objects.create(
        project=active_project,
        title="Closed risk",
        probability=1,
        impact=1,
        status=Risk.Status.CLOSED,
    )
    Transaction.objects.create(
        workspace=workspace,
        project=active_project,
        title="Spend",
        amount=200,
        transaction_type=Transaction.TransactionType.EXPENSE,
        transaction_date=date.today(),
    )
    Notification.objects.create(
        user=user,
        workspace=workspace,
        notification_type=Notification.NotificationType.RISK,
        title="Alert",
        link=f"/projects/{active_project.id}",
        is_read=False,
    )

    response = authenticated_client.get("/api/workspace/dashboard/")
    assert response.status_code == status.HTTP_200_OK
    body = response.data
    assert body["summary"]["overdue_count"] == 1
    assert body["summary"]["open_risk_count"] == 1
    # Manual alert + signal for the high open risk
    assert body["summary"]["unread_notification_count"] == 2
    assert body["overdue_tasks"][0]["title"] == "Late task"
    assert body["top_risks"][0]["title"] == "Big risk"
    assert body["project_health"][0]["project_id"] == active_project.id
    assert body["project_health"][0]["cpi"] is not None


@pytest.mark.django_db
def test_workspace_dashboard_isolates_workspaces(
    authenticated_client, workspace, other_user
):
    other_ws = other_user.workspace_memberships.first().workspace
    ProjectFactory(workspace=other_ws, manager=other_user, name="Other")
    response = authenticated_client.get("/api/workspace/dashboard/")
    assert response.status_code == status.HTTP_200_OK
    assert all(
        item["name"] != "Other" for item in response.data["project_health"]
    )


@pytest.mark.django_db
def test_viewer_can_read_dashboard(workspace, user):
    viewer = UserFactory(email="dashviewer@example.com", username="dashviewer")
    set_active_workspace(viewer, workspace)
    WorkspaceMemberFactory(
        workspace=workspace,
        user=viewer,
        role=WorkspaceMember.Role.VIEWER,
    )
    client = APIClient()
    client.force_authenticate(user=viewer)
    client.credentials(HTTP_X_WORKSPACE_ID=str(workspace.id))
    response = client.get("/api/workspace/dashboard/")
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_notifications_scoped_by_workspace(authenticated_client, workspace, user):
    other = UserFactory(email="n2@example.com", username="n2")
    other_ws = other.workspace_memberships.first().workspace
    Notification.objects.create(
        user=user,
        workspace=workspace,
        notification_type=Notification.NotificationType.INVITE,
        title="Mine",
    )
    Notification.objects.create(
        user=user,
        workspace=other_ws,
        notification_type=Notification.NotificationType.INVITE,
        title="Other",
    )
    response = authenticated_client.get("/api/notifications/")
    assert response.status_code == status.HTTP_200_OK
    titles = [item["title"] for item in response.data["results"]]
    assert "Mine" in titles
    assert "Other" not in titles
