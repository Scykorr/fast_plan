"""Migrate running process instances onto a newly published deployment (lite)."""

from __future__ import annotations

import re

from SpiffWorkflow.bpmn.workflow import BpmnWorkflow

from process.engine import _advance, load_spec, serialize_workflow
from process.models import ProcessDefinition, ProcessDeployment, ProcessInstance, UserTask

_ID_RE = re.compile(r'\bid="([^"]+)"')


def bpmn_element_ids(xml: str) -> set[str]:
    return set(_ID_RE.findall(xml or ""))


def migrate_running_instances(
    definition: ProcessDefinition,
    new_deployment: ProcessDeployment,
) -> dict:
    """
    Opt-in lite migration on publish:
    - ACTIVE top-level instances still on older deployments
    - Requires open UserTask bpmn_ids ⊆ new BPMN (else skip)
    - Restarts workflow on the new deployment, keeps instance.id + data
    - Stale OPEN UserTasks are cancelled; READY tasks re-synced from new spec
    """
    new_ids = bpmn_element_ids(new_deployment.bpmn_xml)
    running = (
        ProcessInstance.objects.filter(
            workspace=definition.workspace,
            deployment__definition=definition,
            status=ProcessInstance.Status.ACTIVE,
            parent__isnull=True,
        )
        .exclude(deployment_id=new_deployment.id)
        .select_related("deployment")
    )

    running_list = list(running)
    migrated: list[dict] = []
    skipped: list[dict] = []

    for instance in running_list:
        open_tasks = list(
            UserTask.objects.filter(
                instance=instance, status=UserTask.Status.OPEN
            ).select_related("activity")
        )
        required: set[str] = set()
        for task in open_tasks:
            payload = (task.activity.payload if task.activity_id else {}) or {}
            bpmn_id = str(payload.get("bpmn_id") or "").strip()
            if bpmn_id:
                required.add(bpmn_id)
        missing = sorted(required - new_ids)
        if missing:
            skipped.append(
                {
                    "instance_id": instance.id,
                    "reason": "missing_elements",
                    "missing": missing,
                }
            )
            continue
        try:
            UserTask.objects.filter(
                instance=instance, status=UserTask.Status.OPEN
            ).update(status=UserTask.Status.CANCELLED)
            spec, subprocess_specs = load_spec(
                new_deployment.bpmn_xml, new_deployment.process_id
            )
            workflow = BpmnWorkflow(spec, subprocess_specs=subprocess_specs or None)
            if instance.data:
                workflow.data.update(dict(instance.data))
            instance.deployment = new_deployment
            instance.state_json = serialize_workflow(workflow)
            instance.error_message = ""
            instance.save(
                update_fields=["deployment", "state_json", "error_message"]
            )
            _advance(instance, workflow)
            migrated.append({"instance_id": instance.id})
        except Exception as exc:  # noqa: BLE001
            skipped.append(
                {
                    "instance_id": instance.id,
                    "reason": "engine_error",
                    "detail": str(exc)[:300],
                }
            )

    return {
        "migrated": migrated,
        "skipped": skipped,
        "migrated_count": len(migrated),
        "skipped_count": len(skipped),
        "prior_active_count": len(running_list),
    }
