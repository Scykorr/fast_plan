"""Waterfall / predictive methodology: seed, gates, schedule lock."""

import pytest
from rest_framework import status

from projects.models import PhaseGate, Project, ProjectBaseline, WBSNode


@pytest.mark.django_db
def test_seed_waterfall_phases_and_gate_pass(authenticated_client, workspace, user):
    project = Project.objects.create(
        workspace=workspace,
        name="WF project",
        manager=user,
        methodology=Project.Methodology.PREDICTIVE,
    )
    seed = authenticated_client.post(
        f"/api/projects/{project.id}/waterfall/",
        {"set_methodology": True},
        format="json",
    )
    assert seed.status_code == status.HTTP_201_CREATED
    project.refresh_from_db()
    phases = list(
        WBSNode.objects.filter(project=project, phase_key__isnull=False).order_by(
            "phase_order"
        )
    )
    assert len(phases) == 5
    assert phases[0].phase_key == WBSNode.PhaseKey.REQUIREMENTS
    assert phases[0].gate_status == WBSNode.GateStatus.OPEN
    assert phases[1].gate_status == WBSNode.GateStatus.LOCKED

    overview = authenticated_client.get(f"/api/projects/{project.id}/waterfall/")
    assert overview.status_code == status.HTTP_200_OK
    assert len(overview.data["phases"]) == 5

    # Cannot create WP under locked Design phase
    blocked = authenticated_client.post(
        f"/api/projects/{project.id}/wbs/",
        {"title": "Early design", "parent_id": phases[1].id},
        format="json",
    )
    assert blocked.status_code == status.HTTP_400_BAD_REQUEST

    # Can create under open Requirements
    ok = authenticated_client.post(
        f"/api/projects/{project.id}/wbs/",
        {"title": "Elicit needs", "parent_id": phases[0].id},
        format="json",
    )
    assert ok.status_code == status.HTTP_201_CREATED

    decide = authenticated_client.post(
        f"/api/projects/{project.id}/waterfall/gates/",
        {
            "wbs_phase_node_id": phases[0].id,
            "decision": "pass",
            "comment": "Req signed off",
            "create_baseline": True,
            "lock_schedule": True,
        },
        format="json",
    )
    assert decide.status_code == status.HTTP_200_OK
    assert decide.data["gate"]["decision"] == PhaseGate.Decision.PASS
    assert decide.data["schedule_locked"] is True
    phases[1].refresh_from_db()
    assert phases[1].gate_status == WBSNode.GateStatus.OPEN
    project.refresh_from_db()
    assert project.schedule_locked is True
    assert ProjectBaseline.objects.filter(project=project).exists()

    # Structure edit blocked while locked
    locked_edit = authenticated_client.patch(
        f"/api/wbs/{phases[0].id}/",
        {"title": "Requirements v2"},
        format="json",
    )
    assert locked_edit.status_code == status.HTTP_409_CONFLICT

    # Approve CR unlocks
    cr = authenticated_client.post(
        f"/api/projects/{project.id}/change-requests/",
        {"title": "Rename phase", "change_type": "scope"},
        format="json",
    )
    assert cr.status_code == status.HTTP_201_CREATED
    decide_cr = authenticated_client.post(
        f"/api/change-requests/{cr.data['id']}/decide/",
        {"action": "approve", "note": "ok"},
        format="json",
    )
    assert decide_cr.status_code == status.HTTP_200_OK
    project.refresh_from_db()
    assert project.schedule_locked is False

    unlocked = authenticated_client.patch(
        f"/api/wbs/{phases[0].id}/",
        {"title": "Requirements v2"},
        format="json",
    )
    assert unlocked.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_create_project_with_seed_waterfall(authenticated_client, workspace):
    resp = authenticated_client.post(
        "/api/projects/",
        {
            "name": "Seeded WF",
            "methodology": "predictive",
            "seed_waterfall": True,
        },
        format="json",
    )
    assert resp.status_code == status.HTTP_201_CREATED
    assert resp.data["methodology"] == "predictive"
    project_id = resp.data["id"]
    overview = authenticated_client.get(f"/api/projects/{project_id}/waterfall/")
    assert overview.status_code == status.HTTP_200_OK
    assert len(overview.data["phases"]) == 5


@pytest.mark.django_db
def test_gate_fail_keeps_phase_open(authenticated_client, workspace, user):
    project = Project.objects.create(
        workspace=workspace, name="Fail gate", manager=user
    )
    authenticated_client.post(
        f"/api/projects/{project.id}/waterfall/", {}, format="json"
    )
    phase = WBSNode.objects.get(
        project=project, phase_key=WBSNode.PhaseKey.REQUIREMENTS
    )
    fail = authenticated_client.post(
        f"/api/projects/{project.id}/waterfall/gates/",
        {"wbs_phase_node_id": phase.id, "decision": "fail", "comment": "gaps"},
        format="json",
    )
    assert fail.status_code == status.HTTP_200_OK
    phase.refresh_from_db()
    assert phase.gate_status == WBSNode.GateStatus.OPEN
    assert fail.data["gate"]["decision"] == "fail"


@pytest.mark.django_db
def test_waterfall_phase_add_rename_delete(authenticated_client, workspace, user):
    project = Project.objects.create(
        workspace=workspace, name="Editable phases", manager=user
    )
    authenticated_client.post(
        f"/api/projects/{project.id}/waterfall/", {}, format="json"
    )
    add = authenticated_client.post(
        f"/api/projects/{project.id}/waterfall/phases/",
        {"title": "Deployment", "duration_days": 7},
        format="json",
    )
    assert add.status_code == status.HTTP_201_CREATED
    assert add.data["title"] == "Deployment"
    assert add.data["phase_order"] == 6
    assert add.data["gate_status"] == WBSNode.GateStatus.LOCKED
    phase_id = add.data["id"]

    rename = authenticated_client.patch(
        f"/api/projects/{project.id}/waterfall/phases/{phase_id}/",
        {"title": "Release & Deploy"},
        format="json",
    )
    assert rename.status_code == status.HTTP_200_OK
    assert rename.data["title"] == "Release & Deploy"
    node = WBSNode.objects.get(pk=phase_id)
    assert node.children.filter(title="Gate: Release & Deploy").exists()

    # Rename still works when locked
    req = WBSNode.objects.get(
        project=project, phase_key=WBSNode.PhaseKey.REQUIREMENTS
    )
    authenticated_client.post(
        f"/api/projects/{project.id}/waterfall/gates/",
        {
            "wbs_phase_node_id": req.id,
            "decision": "pass",
            "lock_schedule": True,
        },
        format="json",
    )
    project.refresh_from_db()
    assert project.schedule_locked is True
    rename_locked = authenticated_client.patch(
        f"/api/projects/{project.id}/waterfall/phases/{phase_id}/",
        {"title": "Deploy"},
        format="json",
    )
    assert rename_locked.status_code == status.HTTP_200_OK

    delete_locked = authenticated_client.delete(
        f"/api/projects/{project.id}/waterfall/phases/{phase_id}/",
    )
    assert delete_locked.status_code == status.HTTP_409_CONFLICT

    # Unlock via CR then delete
    cr = authenticated_client.post(
        f"/api/projects/{project.id}/change-requests/",
        {"title": "Drop deploy phase", "change_type": "scope"},
        format="json",
    )
    authenticated_client.post(
        f"/api/change-requests/{cr.data['id']}/decide/",
        {"action": "approve"},
        format="json",
    )
    delete_ok = authenticated_client.delete(
        f"/api/projects/{project.id}/waterfall/phases/{phase_id}/",
    )
    assert delete_ok.status_code == status.HTTP_204_NO_CONTENT
    assert not WBSNode.objects.filter(pk=phase_id).exists()
    assert (
        WBSNode.objects.filter(project=project, phase_order__isnull=False).count()
        == 5
    )
