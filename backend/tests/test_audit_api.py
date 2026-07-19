import pytest
from rest_framework import status
from rest_framework.test import APIClient

from audit.models import AuditLogEntry
from audit.services import log_audit
from finance.models import Transaction
from projects.models import Project, Risk
from tests.factories import UserFactory, WorkspaceMemberFactory
from workspaces.models import WorkspaceMember
from workspaces.services import set_active_workspace


@pytest.fixture
def project(workspace, user):
    return Project.objects.create(
        workspace=workspace,
        name="Audit Project",
        manager=user,
        budget=10000,
    )


@pytest.fixture
def viewer_client(workspace):
    user = UserFactory(email="viewer-audit@example.com", username="viewer_audit")
    set_active_workspace(user, workspace)
    WorkspaceMemberFactory(workspace=workspace, user=user, role=WorkspaceMember.Role.VIEWER)
    client = APIClient()
    client.force_authenticate(user=user)
    client.credentials(HTTP_X_WORKSPACE_ID=str(workspace.id))
    return client


@pytest.mark.django_db
def test_log_audit_helper_creates_entry(workspace, user):
    entry = log_audit(
        workspace, user, "test.action", "TestEntity", 1, summary="did a thing"
    )
    assert AuditLogEntry.objects.filter(pk=entry.pk).exists()
    assert entry.actor_id == user.id
    assert entry.workspace_id == workspace.id


@pytest.mark.django_db
def test_audit_log_list_paginated(authenticated_client, workspace, user):
    for i in range(3):
        log_audit(workspace, user, "test.action", "TestEntity", i, summary=f"entry {i}")
    response = authenticated_client.get("/api/workspace/audit/")
    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 3
    assert len(response.data["results"]) == 3


@pytest.mark.django_db
def test_viewer_cannot_read_audit_log(viewer_client, workspace, user):
    log_audit(workspace, user, "test.action", "TestEntity", 1)
    response = viewer_client.get("/api/workspace/audit/")
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_finance_transaction_mutations_are_audited(authenticated_client, project):
    created = authenticated_client.post(
        "/api/finance/transactions/",
        {
            "project_id": project.id,
            "title": "Hosting",
            "amount": "100.00",
            "transaction_type": "expense",
            "transaction_date": "2026-01-01",
        },
        format="json",
    )
    assert created.status_code == status.HTTP_201_CREATED
    tx_id = created.data["id"]
    assert AuditLogEntry.objects.filter(action="transaction.create", entity_id=tx_id).exists()

    updated = authenticated_client.patch(
        f"/api/finance/transactions/{tx_id}/",
        {"title": "Hosting Pro"},
        format="json",
    )
    assert updated.status_code == status.HTTP_200_OK
    assert AuditLogEntry.objects.filter(action="transaction.update", entity_id=tx_id).exists()

    deleted = authenticated_client.delete(f"/api/finance/transactions/{tx_id}/")
    assert deleted.status_code == status.HTTP_204_NO_CONTENT
    assert AuditLogEntry.objects.filter(action="transaction.delete", entity_id=tx_id).exists()
    assert not Transaction.objects.filter(pk=tx_id).exists()


@pytest.mark.django_db
def test_wbs_mutations_are_audited(authenticated_client, project):
    root_id = project.wbs_nodes.get(parent__isnull=True).id
    created = authenticated_client.post(
        f"/api/projects/{project.id}/wbs/",
        {"title": "New task", "parent_id": root_id, "node_type": "work_package"},
        format="json",
    )
    assert created.status_code == status.HTTP_201_CREATED
    node = project.wbs_nodes.get(title="New task")
    assert AuditLogEntry.objects.filter(action="wbs.create", entity_id=node.id).exists()

    updated = authenticated_client.patch(
        f"/api/wbs/{node.id}/",
        {"title": "Renamed task"},
        format="json",
    )
    assert updated.status_code == status.HTTP_200_OK
    assert AuditLogEntry.objects.filter(action="wbs.update", entity_id=node.id).exists()

    deleted = authenticated_client.delete(f"/api/wbs/{node.id}/")
    assert deleted.status_code == status.HTTP_204_NO_CONTENT
    assert AuditLogEntry.objects.filter(action="wbs.delete", entity_id=node.id).exists()


@pytest.mark.django_db
def test_risk_mutations_are_audited(authenticated_client, project):
    created = authenticated_client.post(
        f"/api/projects/{project.id}/risks/",
        {"title": "Scope creep", "probability": 3, "impact": 3},
        format="json",
    )
    assert created.status_code == status.HTTP_201_CREATED
    risk_id = created.data["id"]
    assert AuditLogEntry.objects.filter(action="risk.create", entity_id=risk_id).exists()

    updated = authenticated_client.patch(
        f"/api/risks/{risk_id}/",
        {"status": "mitigated"},
        format="json",
    )
    assert updated.status_code == status.HTTP_200_OK
    assert AuditLogEntry.objects.filter(action="risk.update", entity_id=risk_id).exists()

    deleted = authenticated_client.delete(f"/api/risks/{risk_id}/")
    assert deleted.status_code == status.HTTP_204_NO_CONTENT
    assert AuditLogEntry.objects.filter(action="risk.delete", entity_id=risk_id).exists()
    assert not Risk.objects.filter(pk=risk_id).exists()


@pytest.mark.django_db
def test_invitation_and_member_mutations_are_audited(authenticated_client, workspace, other_user):
    invited = authenticated_client.post(
        "/api/workspace/invitations/",
        {"email": other_user.email, "role": "editor"},
        format="json",
    )
    assert invited.status_code == status.HTTP_201_CREATED
    invitation_id = invited.data["id"]
    assert AuditLogEntry.objects.filter(action="invitation.create", entity_id=invitation_id).exists()

    revoked = authenticated_client.delete(f"/api/workspace/invitations/{invitation_id}/")
    assert revoked.status_code == status.HTTP_204_NO_CONTENT
    assert AuditLogEntry.objects.filter(action="invitation.revoke", entity_id=invitation_id).exists()

    member = WorkspaceMemberFactory(workspace=workspace, user=other_user, role=WorkspaceMember.Role.VIEWER)
    role_changed = authenticated_client.patch(
        f"/api/workspace/members/{member.id}/",
        {"role": "editor"},
        format="json",
    )
    assert role_changed.status_code == status.HTTP_200_OK
    assert AuditLogEntry.objects.filter(action="member.role_change", entity_id=member.id).exists()

    removed = authenticated_client.delete(f"/api/workspace/members/{member.id}/")
    assert removed.status_code == status.HTTP_204_NO_CONTENT
    assert AuditLogEntry.objects.filter(action="member.remove", entity_id=member.id).exists()


@pytest.mark.django_db
def test_audit_log_has_no_mutation_endpoints(authenticated_client, workspace, user):
    entry = log_audit(workspace, user, "test.action", "TestEntity", 1)
    response = authenticated_client.patch(f"/api/workspace/audit/{entry.id}/", {}, format="json")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    response = authenticated_client.delete(f"/api/workspace/audit/{entry.id}/")
    assert response.status_code == status.HTTP_404_NOT_FOUND
