import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status

from attachments.models import WorkItemAttachment
from projects.models import Project


@pytest.fixture
def project(workspace, user):
    return Project.objects.create(
        workspace=workspace,
        name="Attachment Project",
        manager=user,
        budget=1000,
    )


@pytest.fixture
def wbs_node(project):
    return project.wbs_nodes.get(parent__isnull=True)


def _upload(name="note.txt", content=b"hello world", content_type="text/plain"):
    return SimpleUploadedFile(name, content, content_type=content_type)


@pytest.mark.django_db
def test_upload_and_list_wbs_attachment(authenticated_client, wbs_node):
    response = authenticated_client.post(
        f"/api/wbs/{wbs_node.id}/attachments/",
        {"file": _upload()},
        format="multipart",
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["name"] == "note.txt"
    assert WorkItemAttachment.objects.filter(wbs_node=wbs_node).count() == 1

    listed = authenticated_client.get(f"/api/wbs/{wbs_node.id}/attachments/")
    assert listed.status_code == status.HTTP_200_OK
    assert len(listed.data) == 1


@pytest.mark.django_db
def test_upload_and_list_card_attachment(authenticated_client, card):
    response = authenticated_client.post(
        f"/api/cards/{card.id}/attachments/",
        {"file": _upload("image.png", b"binarydata", "image/png")},
        format="multipart",
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert WorkItemAttachment.objects.filter(card=card).count() == 1

    listed = authenticated_client.get(f"/api/cards/{card.id}/attachments/")
    assert listed.status_code == status.HTTP_200_OK
    assert len(listed.data) == 1


@pytest.mark.django_db
def test_delete_attachment(authenticated_client, wbs_node):
    created = authenticated_client.post(
        f"/api/wbs/{wbs_node.id}/attachments/",
        {"file": _upload()},
        format="multipart",
    )
    attachment_id = created.data["id"]
    deleted = authenticated_client.delete(f"/api/attachments/{attachment_id}/")
    assert deleted.status_code == status.HTTP_204_NO_CONTENT
    assert not WorkItemAttachment.objects.filter(pk=attachment_id).exists()


@pytest.mark.django_db
def test_attachment_over_limit_rejected(authenticated_client, wbs_node, settings):
    settings.ATTACHMENT_MAX_BYTES = 10
    response = authenticated_client.post(
        f"/api/wbs/{wbs_node.id}/attachments/",
        {"file": _upload(content=b"this content is definitely over ten bytes")},
        format="multipart",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_viewer_cannot_upload_attachment(authenticated_client, wbs_node, workspace):
    from tests.factories import UserFactory, WorkspaceMemberFactory
    from workspaces.models import WorkspaceMember
    from workspaces.services import set_active_workspace
    from rest_framework.test import APIClient

    viewer = UserFactory(email="viewer-att@example.com", username="viewer_att")
    set_active_workspace(viewer, workspace)
    WorkspaceMemberFactory(workspace=workspace, user=viewer, role=WorkspaceMember.Role.VIEWER)
    client = APIClient()
    client.force_authenticate(user=viewer)
    client.credentials(HTTP_X_WORKSPACE_ID=str(workspace.id))

    response = client.post(
        f"/api/wbs/{wbs_node.id}/attachments/",
        {"file": _upload()},
        format="multipart",
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
