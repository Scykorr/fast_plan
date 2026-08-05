"""Process service helpers."""

from __future__ import annotations

from django.db import transaction
from rest_framework.exceptions import ValidationError

from process.engine import parse_process_id
from process.models import ProcessDefinition, ProcessDeployment, ProcessWorkNode


def deploy_if_needed(definition: ProcessDefinition, *, user=None) -> ProcessDeployment:
    """Create an immutable deployment for the current definition version."""
    existing = definition.deployments.filter(version=definition.version).first()
    if existing:
        return existing
    process_id = definition.process_id or parse_process_id(definition.bpmn_xml)
    if not definition.process_id:
        definition.process_id = process_id
        definition.save(update_fields=["process_id"])
    return ProcessDeployment.objects.create(
        definition=definition,
        workspace=definition.workspace,
        version=definition.version,
        bpmn_xml=definition.bpmn_xml,
        process_id=process_id,
        deployed_by=user,
    )


def publish_definition(
    definition: ProcessDefinition,
    *,
    user=None,
    migrate_running: bool = False,
) -> tuple[ProcessDeployment, dict]:
    definition.is_published = True
    if not definition.process_id:
        definition.process_id = parse_process_id(definition.bpmn_xml)
    definition.save(update_fields=["is_published", "process_id", "updated_at"])
    deployment = deploy_if_needed(definition, user=user)
    migration: dict = {
        "migrated_count": 0,
        "skipped_count": 0,
        "migrated": [],
        "skipped": [],
        "prior_active_count": 0,
    }
    if migrate_running:
        from process.instance_migration import migrate_running_instances

        migration = migrate_running_instances(definition, deployment)
    else:
        from process.models import ProcessInstance

        migration["prior_active_count"] = ProcessInstance.objects.filter(
            workspace=definition.workspace,
            deployment__definition=definition,
            status=ProcessInstance.Status.ACTIVE,
            parent__isnull=True,
        ).exclude(deployment_id=deployment.id).count()
    return deployment, migration


@transaction.atomic
def move_process_work_node(node: ProcessWorkNode, *, position: int) -> ProcessWorkNode:
    """Reorder among siblings only (no reparent — preserves BPMN hierarchy)."""
    siblings = list(
        ProcessWorkNode.objects.filter(
            instance_id=node.instance_id,
            parent_id=node.parent_id,
        )
        .exclude(pk=node.pk)
        .order_by("position", "id")
    )
    position = min(max(int(position), 0), len(siblings))
    siblings.insert(position, node)
    for index, sibling in enumerate(siblings):
        if sibling.position != index:
            ProcessWorkNode.objects.filter(pk=sibling.pk).update(position=index)
    node.refresh_from_db()
    return node


def require_sibling_position(raw) -> int:
    try:
        return int(raw)
    except (TypeError, ValueError) as exc:
        raise ValidationError({"position": "Invalid"}) from exc
