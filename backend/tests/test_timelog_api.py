import pytest
from datetime import date
from rest_framework import status

from projects.models import Project
from timelog.models import TimeEntry


@pytest.fixture
def project(workspace, user):
    return Project.objects.create(
        workspace=workspace,
        name="Timelog Project",
        manager=user,
        budget=1000,
    )


@pytest.fixture
def wbs_node(project):
    return project.wbs_nodes.get(parent__isnull=True)


@pytest.mark.django_db
def test_create_and_list_time_entry(authenticated_client, wbs_node):
    response = authenticated_client.post(
        "/api/workspace/time-entries/",
        {
            "wbs_node": wbs_node.id,
            "hours": "2.5",
            "work_date": date.today().isoformat(),
            "notes": "Worked on scope",
        },
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert TimeEntry.objects.filter(wbs_node=wbs_node).count() == 1

    listed = authenticated_client.get("/api/workspace/time-entries/")
    assert listed.status_code == status.HTTP_200_OK
    assert len(listed.data) == 1
    assert listed.data[0]["hours"] == "2.50"


@pytest.mark.django_db
def test_negative_hours_rejected(authenticated_client, wbs_node):
    response = authenticated_client.post(
        "/api/workspace/time-entries/",
        {"wbs_node": wbs_node.id, "hours": "-1", "work_date": date.today().isoformat()},
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_update_and_delete_time_entry(authenticated_client, wbs_node):
    created = authenticated_client.post(
        "/api/workspace/time-entries/",
        {"wbs_node": wbs_node.id, "hours": "1", "work_date": date.today().isoformat()},
        format="json",
    )
    entry_id = created.data["id"]

    updated = authenticated_client.patch(
        f"/api/workspace/time-entries/{entry_id}/",
        {"hours": "3", "notes": "Updated"},
        format="json",
    )
    assert updated.status_code == status.HTTP_200_OK
    assert updated.data["hours"] == "3.00"

    deleted = authenticated_client.delete(f"/api/workspace/time-entries/{entry_id}/")
    assert deleted.status_code == status.HTTP_204_NO_CONTENT
    assert not TimeEntry.objects.filter(pk=entry_id).exists()


@pytest.mark.django_db
def test_capacity_report_includes_logged_hours(authenticated_client, wbs_node, workspace, user):
    week_start = date.today()
    TimeEntry.objects.create(
        workspace=workspace,
        user=user,
        wbs_node=wbs_node,
        hours=4,
        work_date=week_start,
    )
    response = authenticated_client.get("/api/workspace/capacity/")
    assert response.status_code == status.HTTP_200_OK
    member = next(m for m in response.data["members"] if m["user_id"] == user.id)
    assert member["logged_hours"] == 4.0


@pytest.mark.django_db
def test_other_user_cannot_modify_time_entry(authenticated_client, wbs_node, workspace):
    from tests.factories import UserFactory, WorkspaceMemberFactory
    from workspaces.models import WorkspaceMember
    from workspaces.services import set_active_workspace

    editor = UserFactory(email="editor-time@example.com", username="editor_time")
    set_active_workspace(editor, workspace)
    WorkspaceMemberFactory(workspace=workspace, user=editor, role=WorkspaceMember.Role.EDITOR)

    created = authenticated_client.post(
        "/api/workspace/time-entries/",
        {"wbs_node": wbs_node.id, "hours": "1", "work_date": date.today().isoformat()},
        format="json",
    )
    entry_id = created.data["id"]

    from rest_framework.test import APIClient

    editor_client = APIClient()
    editor_client.force_authenticate(user=editor)
    editor_client.credentials(HTTP_X_WORKSPACE_ID=str(workspace.id))
    response = editor_client.delete(f"/api/workspace/time-entries/{entry_id}/")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
