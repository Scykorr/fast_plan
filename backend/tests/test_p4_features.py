"""P4: CSV import, guest share links, PERT, AI drafts, project roles."""

from datetime import date, timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from finance.imports import import_transactions_csv
from finance.models import Transaction
from projects.imports import import_jira_csv, import_wbs_csv
from projects.models import Project, ProjectMember, ProjectShareLink, ScheduleActivity
from projects.permissions import has_project_min_role
from projects.pert import compute_pert_network
from tests.factories import UserFactory, WorkspaceMemberFactory
from workspaces.models import ExchangeRate, Workspace, WorkspaceMember
from workspaces.services import set_active_workspace


@pytest.fixture
def viewer_user(db, workspace):
    user = UserFactory(email="viewer@example.com", username="viewer")
    set_active_workspace(user, workspace)
    WorkspaceMemberFactory(
        workspace=workspace,
        user=user,
        role=WorkspaceMember.Role.VIEWER,
    )
    return user


@pytest.fixture
def viewer_client(viewer_user):
    client = APIClient()
    client.force_authenticate(user=viewer_user)
    client.credentials(HTTP_X_WORKSPACE_ID=str(viewer_user.active_workspace_id))
    return client


@pytest.fixture
def project(workspace, user):
    return Project.objects.create(
        workspace=workspace,
        name="P4 Project",
        description="Import and share tests",
        manager=user,
        budget=50000,
    )


def _csv_file(content: str, name: str = "import.csv") -> SimpleUploadedFile:
    return SimpleUploadedFile(name, content.encode("utf-8"), content_type="text/csv")


WBS_CSV = """code,title,node_type,assignee,status,progress,start_date,end_date
1,P4 Project Root,summary,,,0,,
1.1,Imported Task,work_package,,,50,2026-08-01,2026-08-10
"""

JIRA_CSV = """Issue Type,Issue key,Summary,Parent key
Epic,P4-1,Platform Epic,
Story,P4-2,User story,P4-1
Task,P4-3,Implementation,P4-2
"""


def _transactions_csv(project_id: int) -> str:
    today = date.today().isoformat()
    return f"""id,title,amount,transaction_type,category,transaction_date,project_id,notes
,Hosting,1200.00,expense,infra,{today},,Monthly hosting
,Project expense,500.00,expense,,{today},{project_id},Linked to project
"""


@pytest.mark.django_db
def test_import_wbs_csv_creates_and_updates_nodes(project):
    root = project.wbs_nodes.get(code="1")
    result = import_wbs_csv(project, WBS_CSV.encode("utf-8"))

    assert result["created"] == 1
    assert result["updated"] == 1
    assert result["errors"] == []

    task = project.wbs_nodes.get(code="1.1")
    assert task.title == "Imported Task"
    assert task.parent_id == root.id
    schedule = ScheduleActivity.objects.get(wbs_node=task)
    assert schedule.progress == 50
    assert schedule.start_date == date(2026, 8, 1)
    assert schedule.end_date == date(2026, 8, 10)


@pytest.mark.django_db
def test_import_wbs_csv_api(authenticated_client, project):
    response = authenticated_client.post(
        f"/api/projects/{project.id}/import/",
        {"file": _csv_file(WBS_CSV)},
        format="multipart",
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.data["created"] == 1
    assert project.wbs_nodes.filter(code="1.1", title="Imported Task").exists()


@pytest.mark.django_db
def test_import_wbs_csv_missing_file(authenticated_client, project):
    response = authenticated_client.post(
        f"/api/projects/{project.id}/import/",
        {},
        format="multipart",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "file" in response.data


@pytest.mark.django_db
def test_import_jira_csv_creates_hierarchy(project):
    result = import_jira_csv(project, JIRA_CSV.encode("utf-8"))

    assert result["created"] == 3
    assert result["format"] == "jira"
    assert result["errors"] == []
    story = project.wbs_nodes.get(code="P4-2")
    assert story.title == "User story"
    assert story.parent.code == "P4-1"


@pytest.mark.django_db
def test_import_jira_csv_api(authenticated_client, project):
    response = authenticated_client.post(
        f"/api/projects/{project.id}/import/",
        {"file": _csv_file(JIRA_CSV), "format": "jira"},
        format="multipart",
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.data["format"] == "jira"
    assert project.wbs_nodes.filter(code="P4-3", title="Implementation").exists()


@pytest.mark.django_db
def test_import_transactions_csv(project):
    raw = _transactions_csv(project.id).encode("utf-8")
    result = import_transactions_csv(project.workspace, raw)

    assert result["created"] == 2
    assert result["errors"] == []
    assert Transaction.objects.filter(workspace=project.workspace).count() == 2
    assert Transaction.objects.filter(project=project, title="Project expense").exists()


@pytest.mark.django_db
def test_import_transactions_csv_api(authenticated_client, project):
    content = _transactions_csv(project.id)
    response = authenticated_client.post(
        "/api/finance/transactions/import/",
        {"file": _csv_file(content, "transactions.csv")},
        format="multipart",
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.data["created"] == 2


@pytest.mark.django_db
def test_create_list_and_revoke_share_link(authenticated_client, project, user):
    created = authenticated_client.post(
        f"/api/projects/{project.id}/share-links/",
        {"label": "Stakeholders"},
        format="json",
    )
    assert created.status_code == status.HTTP_201_CREATED
    token = created.data["token"]
    assert created.data["url_path"] == f"/share/{token}"
    assert ProjectShareLink.objects.filter(project=project, token=token).exists()

    listed = authenticated_client.get(f"/api/projects/{project.id}/share-links/")
    assert listed.status_code == status.HTTP_200_OK
    assert len(listed.data) == 1
    assert listed.data[0]["label"] == "Stakeholders"

    deleted = authenticated_client.delete(
        f"/api/projects/{project.id}/share-links/{created.data['id']}/"
    )
    assert deleted.status_code == status.HTTP_204_NO_CONTENT
    link = ProjectShareLink.objects.get(pk=created.data["id"])
    assert link.revoked_at is not None


@pytest.mark.django_db
def test_public_status_report_without_auth(project, user):
    link = ProjectShareLink.objects.create(
        project=project,
        token="public-test-token",
        label="Guest",
        created_by=user,
    )
    client = APIClient()
    response = client.get(f"/api/share/{link.token}/")
    assert response.status_code == status.HTTP_200_OK
    assert response.data["share"]["project_name"] == project.name
    assert response.data["share"]["label"] == "Guest"
    link.refresh_from_db()
    assert link.last_accessed_at is not None


@pytest.mark.django_db
def test_public_status_report_rejects_revoked_link(project, user):
    link = ProjectShareLink.objects.create(
        project=project,
        token="revoked-token",
        label="Old",
        created_by=user,
        revoked_at=timezone.now(),
    )
    response = APIClient().get(f"/api/share/{link.token}/")
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_public_status_report_rejects_expired_link(project, user):
    link = ProjectShareLink.objects.create(
        project=project,
        token="expired-token",
        label="Expired",
        created_by=user,
        expires_at=timezone.now() - timedelta(hours=1),
    )
    response = APIClient().get(f"/api/share/{link.token}/")
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_pert_network_api(authenticated_client, project):
    root = project.wbs_nodes.get(code="1")
    authenticated_client.post(
        f"/api/projects/{project.id}/wbs/",
        {"title": "PERT Task", "parent_id": root.id, "node_type": "work_package"},
        format="json",
    )
    response = authenticated_client.get(f"/api/projects/{project.id}/pert/")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data["nodes"]) >= 1
    node = next(item for item in response.data["nodes"] if item["name"] == "PERT Task")
    assert node["most_likely_days"] >= 1
    assert "expected_days" in node
    assert "edges" in response.data
    assert "critical_path_ids" in response.data


@pytest.mark.django_db
def test_compute_pert_network_includes_dependencies(project):
    root = project.wbs_nodes.get(code="1")
    from projects.services import create_work_package
    from projects.models import ActivityDependency

    first = create_work_package(project, root, "A", with_schedule=True, with_kanban_card=False)
    second = create_work_package(project, root, "B", with_schedule=True, with_kanban_card=False)
    act_a = ScheduleActivity.objects.get(wbs_node=first)
    act_b = ScheduleActivity.objects.get(wbs_node=second)
    ActivityDependency.objects.create(
        predecessor=act_a,
        successor=act_b,
        dependency_type="FS",
        lag_days=0,
    )
    network = compute_pert_network(project)
    assert any(edge["from"] == act_a.id and edge["to"] == act_b.id for edge in network["edges"])


@pytest.mark.django_db
def test_ai_draft_risks_heuristic(authenticated_client, project, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    response = authenticated_client.post(
        f"/api/projects/{project.id}/ai-draft/",
        {"target": "risks"},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.data["target"] == "risks"
    assert response.data["source"] == "heuristic"
    assert len(response.data["risks"]) >= 1
    assert "title" in response.data["risks"][0]


@pytest.mark.django_db
def test_ai_draft_charter_heuristic(authenticated_client, project, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    response = authenticated_client.post(
        f"/api/projects/{project.id}/ai-draft/",
        {"target": "charter", "prompt": "Focus on delivery speed"},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.data["target"] == "charter"
    assert response.data["source"] == "heuristic"
    charter = response.data["charter"]
    assert {"goals", "success_criteria", "constraints", "assumptions"} <= set(charter)


@pytest.mark.django_db
def test_ai_draft_invalid_target(authenticated_client, project):
    response = authenticated_client.post(
        f"/api/projects/{project.id}/ai-draft/",
        {"target": "unknown"},
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_ai_draft_wbs_heuristic(authenticated_client, project, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    response = authenticated_client.post(
        f"/api/projects/{project.id}/ai-draft/",
        {"target": "wbs", "prompt": "Mobile app release"},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.data["target"] == "wbs"
    assert response.data["source"] == "heuristic"
    assert len(response.data["nodes"]) >= 3
    assert response.data["saved_prompt"] == "Mobile app release"
    project.refresh_from_db()
    assert project.ai_prompts.get("wbs") == "Mobile app release"


@pytest.mark.django_db
def test_ai_draft_get_prompts(authenticated_client, project):
    project.ai_prompts = {"risks": "Budget focus"}
    project.save(update_fields=["ai_prompts"])
    response = authenticated_client.get(f"/api/projects/{project.id}/ai-draft/")
    assert response.status_code == status.HTTP_200_OK
    assert response.data["ai_prompts"]["risks"] == "Budget focus"


@pytest.mark.django_db
def test_ai_draft_apply_wbs(authenticated_client, project, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    draft = authenticated_client.post(
        f"/api/projects/{project.id}/ai-draft/",
        {"target": "wbs"},
        format="json",
    )
    response = authenticated_client.post(
        f"/api/projects/{project.id}/ai-draft/apply/",
        {
            "target": "wbs",
            "nodes": draft.data["nodes"],
            "dependencies": draft.data["dependencies"],
        },
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.data["created"] >= 1
    assert project.wbs_nodes.filter(code__contains=".").exists()


@pytest.mark.django_db
def test_ai_wbs_refine_heuristic(authenticated_client, project, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    draft = authenticated_client.post(
        f"/api/projects/{project.id}/ai-draft/",
        {"target": "wbs"},
        format="json",
    )
    assert draft.status_code == status.HTTP_200_OK
    initial_count = len(draft.data["nodes"])

    refined = authenticated_client.post(
        f"/api/projects/{project.id}/ai-draft/",
        {
            "target": "wbs",
            "refinement": "добавь этап тестирования",
            "current_draft": {
                "nodes": draft.data["nodes"],
                "dependencies": draft.data["dependencies"],
            },
        },
        format="json",
    )
    assert refined.status_code == status.HTTP_200_OK
    assert refined.data["target"] == "wbs"
    assert refined.data["source"] == "heuristic"
    assert len(refined.data["nodes"]) > initial_count
    assert any("тест" in node["title"].lower() for node in refined.data["nodes"])


@pytest.mark.django_db
def test_ai_wbs_refine_requires_current_draft(authenticated_client, project):
    response = authenticated_client.post(
        f"/api/projects/{project.id}/ai-draft/",
        {"target": "wbs", "refinement": "add QA phase"},
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_project_members_crud(authenticated_client, project, workspace):
    member_user = UserFactory(email="contributor@example.com", username="contributor")
    WorkspaceMemberFactory(
        workspace=workspace,
        user=member_user,
        role=WorkspaceMember.Role.EDITOR,
    )

    created = authenticated_client.post(
        f"/api/projects/{project.id}/members/",
        {"user_id": member_user.id, "role": ProjectMember.Role.CONTRIBUTOR},
        format="json",
    )
    assert created.status_code == status.HTTP_201_CREATED
    assert created.data["role"] == ProjectMember.Role.CONTRIBUTOR

    listed = authenticated_client.get(f"/api/projects/{project.id}/members/")
    assert listed.status_code == status.HTTP_200_OK
    assert len(listed.data) == 1

    updated = authenticated_client.post(
        f"/api/projects/{project.id}/members/",
        {"user_id": member_user.id, "role": ProjectMember.Role.VIEWER},
        format="json",
    )
    assert updated.status_code == status.HTTP_200_OK
    assert updated.data["role"] == ProjectMember.Role.VIEWER

    deleted = authenticated_client.delete(
        f"/api/projects/{project.id}/members/{created.data['id']}/"
    )
    assert deleted.status_code == status.HTTP_204_NO_CONTENT
    assert not ProjectMember.objects.filter(project=project, user=member_user).exists()


@pytest.mark.django_db
def test_has_project_min_role(project, workspace, user):
    viewer = UserFactory(email="proj-viewer@example.com", username="projviewer")
    set_active_workspace(viewer, workspace)
    WorkspaceMemberFactory(
        workspace=workspace,
        user=viewer,
        role=WorkspaceMember.Role.VIEWER,
    )
    ProjectMember.objects.create(
        project=project,
        user=viewer,
        role=ProjectMember.Role.VIEWER,
    )

    assert has_project_min_role(project, user, ProjectMember.Role.MANAGER)
    assert has_project_min_role(project, viewer, ProjectMember.Role.VIEWER)
    assert not has_project_min_role(project, viewer, ProjectMember.Role.CONTRIBUTOR)

    ProjectMember.objects.filter(project=project, user=viewer).update(
        role=ProjectMember.Role.CONTRIBUTOR
    )
    assert has_project_min_role(project, viewer, ProjectMember.Role.CONTRIBUTOR)


@pytest.mark.django_db
def test_workspace_currency_and_exchange_rate(workspace):
    assert workspace.currency == Workspace.Currency.RUB
    rate = ExchangeRate.objects.create(
        workspace=workspace,
        currency=Workspace.Currency.USD,
        rate_to_base="90.50000000",
        as_of=date.today(),
    )
    assert str(rate).startswith("USD@")


@pytest.mark.django_db
def test_viewer_can_read_share_links_but_not_create(viewer_client, project):
    listed = viewer_client.get(f"/api/projects/{project.id}/share-links/")
    assert listed.status_code == status.HTTP_200_OK

    created = viewer_client.post(
        f"/api/projects/{project.id}/share-links/",
        {"label": "Blocked"},
        format="json",
    )
    assert created.status_code == status.HTTP_403_FORBIDDEN
