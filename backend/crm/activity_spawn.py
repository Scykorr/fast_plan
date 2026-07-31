"""Spawn WBS / process from a CRM activity."""

from __future__ import annotations

from rest_framework.exceptions import ValidationError

from crm.models import Activity
from process.engine import start_instance
from process.models import ProcessDefinition, ProcessInstance
from process.services import deploy_if_needed
from projects.models import Project, WBSNode
from projects.services import create_work_package


def spawn_from_activity(
    activity: Activity,
    *,
    mode: str,
    user,
    project_id: int | None = None,
    parent_wbs_id: int | None = None,
    process_key: str | None = None,
) -> dict:
    mode = (mode or "").strip().lower()
    if mode == "wbs":
        return _spawn_wbs(
            activity, user=user, project_id=project_id, parent_wbs_id=parent_wbs_id
        )
    if mode == "process":
        return _spawn_process(activity, user=user, process_key=process_key)
    raise ValidationError({"mode": "Must be 'wbs' or 'process'."})


def _spawn_wbs(activity, *, user, project_id, parent_wbs_id) -> dict:
    project = None
    if project_id:
        project = Project.objects.filter(
            workspace=activity.workspace, pk=project_id
        ).first()
    elif activity.project_id:
        project = activity.project
    if project is None:
        raise ValidationError({"project_id": "Project is required to spawn WBS."})

    parent = None
    if parent_wbs_id:
        parent = WBSNode.objects.filter(project=project, pk=parent_wbs_id).first()
        if parent is None:
            raise ValidationError({"parent_wbs_id": "Parent WBS not found."})
    else:
        parent = project.wbs_nodes.filter(parent__isnull=True).first()
    if parent is None:
        raise ValidationError({"detail": "Project has no root WBS."})

    node = create_work_package(
        project,
        parent,
        activity.subject or f"Activity #{activity.id}",
        WBSNode.NodeType.WORK_PACKAGE,
    )
    if activity.body:
        node.description = activity.body
        node.save(update_fields=["description"])
    if activity.project_id != project.id:
        activity.project = project
        activity.save(update_fields=["project"])
    return {"mode": "wbs", "wbs_node_id": node.id, "project_id": project.id}


def _spawn_process(activity, *, user, process_key) -> dict:
    key = (process_key or "").strip()
    if not key:
        raise ValidationError({"process_key": "Required for process mode."})
    definition = ProcessDefinition.objects.filter(
        workspace=activity.workspace, key=key, is_published=True
    ).first()
    if definition is None:
        raise ValidationError({"process_key": "Published definition not found."})
    deployment = deploy_if_needed(definition, user=user)
    instance = ProcessInstance.objects.create(
        workspace=activity.workspace,
        deployment=deployment,
        business_key=f"activity:{activity.id}",
        deal_id=activity.deal_id,
        project_id=activity.project_id,
        organization_id=activity.organization_id,
        data={
            "activity_id": activity.id,
            "subject": activity.subject,
            "event": "activity.spawn",
        },
        started_by=user,
    )
    start_instance(instance)
    return {
        "mode": "process",
        "instance_id": instance.id,
        "definition_key": definition.key,
    }
