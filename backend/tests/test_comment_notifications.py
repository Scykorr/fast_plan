import pytest
from rest_framework import status

from kanban.models import Card
from notifications.models import Notification
from projects.models import Project
from tests.factories import UserFactory, WorkspaceMemberFactory


@pytest.fixture
def project(workspace, user):
    return Project.objects.create(workspace=workspace, name="Comment Project", manager=user)


@pytest.mark.django_db
def test_wbs_comment_notifies_assignee(authenticated_client, project, workspace):
    assignee = UserFactory(email="assignee@example.com", username="assignee_user")
    WorkspaceMemberFactory(workspace=workspace, user=assignee, role="editor")
    root = project.wbs_nodes.get(code="1")
    root.assignee = assignee
    root.save(update_fields=["assignee"])

    response = authenticated_client.post(
        f"/api/wbs/{root.id}/comments/",
        {"body": "Please review", "kind": "comment"},
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert Notification.objects.filter(
        user=assignee, notification_type=Notification.NotificationType.COMMENT
    ).exists()


@pytest.mark.django_db
def test_wbs_comment_notifies_mentioned_user(authenticated_client, project, workspace):
    mentioned = UserFactory(email="mention@example.com", username="carol")
    WorkspaceMemberFactory(workspace=workspace, user=mentioned, role="editor")
    root = project.wbs_nodes.get(code="1")

    response = authenticated_client.post(
        f"/api/wbs/{root.id}/comments/",
        {"body": "Hey @carol, take a look", "kind": "comment"},
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert Notification.objects.filter(
        user=mentioned, notification_type=Notification.NotificationType.MENTION
    ).exists()


@pytest.mark.django_db
def test_wbs_comment_does_not_notify_author(authenticated_client, project, user):
    root = project.wbs_nodes.get(code="1")
    root.assignee = user
    root.save(update_fields=["assignee"])
    response = authenticated_client.post(
        f"/api/wbs/{root.id}/comments/",
        {"body": f"Note to self @{user.username}", "kind": "comment"},
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert not Notification.objects.filter(user=user).exists()


@pytest.mark.django_db
def test_wbs_comment_mention_dedupes_with_assignee(authenticated_client, project, workspace):
    person = UserFactory(email="both@example.com", username="erin")
    WorkspaceMemberFactory(workspace=workspace, user=person, role="editor")
    root = project.wbs_nodes.get(code="1")
    root.assignee = person
    root.save(update_fields=["assignee"])

    response = authenticated_client.post(
        f"/api/wbs/{root.id}/comments/",
        {"body": "Hi @erin, you're on it", "kind": "comment"},
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert Notification.objects.filter(user=person).count() == 1
    assert Notification.objects.get(user=person).notification_type == (
        Notification.NotificationType.COMMENT
    )


@pytest.mark.django_db
def test_card_comment_notifies_mentioned_user(authenticated_client, workspace):
    mentioned = UserFactory(email="mention2@example.com", username="dave")
    WorkspaceMemberFactory(workspace=workspace, user=mentioned, role="editor")
    board = workspace.boards.first()
    column = board.columns.first()

    card = Card.objects.create(column=column, title="Card A", position=0)
    response = authenticated_client.post(
        f"/api/cards/{card.id}/comments/",
        {"body": "cc @dave", "kind": "comment"},
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert Notification.objects.filter(
        user=mentioned, notification_type=Notification.NotificationType.MENTION
    ).exists()
