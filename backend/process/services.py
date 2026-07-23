"""Process service helpers."""

from __future__ import annotations

from process.engine import parse_process_id
from process.models import ProcessDefinition, ProcessDeployment


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


def publish_definition(definition: ProcessDefinition, *, user=None) -> ProcessDeployment:
    definition.is_published = True
    if not definition.process_id:
        definition.process_id = parse_process_id(definition.bpmn_xml)
    definition.save(update_fields=["is_published", "process_id", "updated_at"])
    return deploy_if_needed(definition, user=user)
