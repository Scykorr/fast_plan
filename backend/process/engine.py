"""SpiffWorkflow BPMN engine integration."""

from __future__ import annotations

import json
import logging
from datetime import timedelta

from django.utils import timezone
from SpiffWorkflow.bpmn.parser.BpmnParser import BpmnParser
from SpiffWorkflow.bpmn.serializer.config import DEFAULT_CONFIG
from SpiffWorkflow.bpmn.serializer.default.task_spec import BpmnTaskSpecConverter
from SpiffWorkflow.bpmn.serializer.workflow import BpmnWorkflowSerializer
from SpiffWorkflow.bpmn.specs.defaults import ServiceTask, UserTask as SpiffUserTask
from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.task import TaskState

from process.adapters import run_service_task
from process.models import ActivityInstance, ProcessInstance, ProcessTimer, UserTask

logger = logging.getLogger("fast_plan")

_config = dict(DEFAULT_CONFIG)
_config[ServiceTask] = BpmnTaskSpecConverter
_serializer = BpmnWorkflowSerializer(BpmnWorkflowSerializer.configure(_config))


def parse_process_id(bpmn_xml: str) -> str:
    parser = BpmnParser()
    parser.add_bpmn_str(_as_bytes(bpmn_xml))
    ids = parser.get_process_ids()
    if not ids:
        raise ValueError("No executable process found in BPMN XML")
    return ids[0]


def _as_bytes(bpmn_xml: str | bytes) -> bytes:
    if isinstance(bpmn_xml, bytes):
        return bpmn_xml
    return bpmn_xml.encode("utf-8")


def load_spec(bpmn_xml: str, process_id: str):
    parser = BpmnParser()
    parser.add_bpmn_str(_as_bytes(bpmn_xml))
    return parser.get_spec(process_id)


def serialize_workflow(workflow: BpmnWorkflow) -> str:
    return _serializer.serialize_json(workflow)


def deserialize_workflow(state_json: str) -> BpmnWorkflow:
    return _serializer.deserialize_json(state_json)


def active_bpmn_element_ids(instance: ProcessInstance) -> list[str]:
    """BPMN element ids with READY / WAITING / STARTED tokens (for diagram highlight)."""
    if not instance.state_json:
        return []
    try:
        workflow = deserialize_workflow(instance.state_json)
    except Exception:  # noqa: BLE001
        return []
    ids: list[str] = []
    for state in (TaskState.READY, TaskState.WAITING, TaskState.STARTED):
        for task in workflow.get_tasks(state=state):
            bpmn_id = getattr(task.task_spec, "bpmn_id", None) or ""
            if not bpmn_id:
                bpmn_id = getattr(task.task_spec, "name", None) or ""
            if bpmn_id and bpmn_id not in ids:
                ids.append(str(bpmn_id))
    return ids


def start_instance(instance: ProcessInstance) -> ProcessInstance:
    deployment = instance.deployment
    spec = load_spec(deployment.bpmn_xml, deployment.process_id)
    workflow = BpmnWorkflow(spec)
    workflow.data.update(instance.data or {})
    _advance(instance, workflow)
    return instance


def complete_user_task(
    user_task: UserTask, *, user, form_data: dict | None = None
) -> ProcessInstance:
    from uuid import UUID

    instance = user_task.instance
    if user_task.status != UserTask.Status.OPEN:
        raise ValueError("Task is not open")
    workflow = deserialize_workflow(instance.state_json)
    try:
        task_id = UUID(str(user_task.spiff_task_id))
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid spiff task id") from exc
    task = workflow.get_task_from_id(task_id)
    if task is None:
        raise ValueError("Spiff task not found")
    if form_data:
        task.data.update(form_data)
        instance.data.update(form_data)
    task.run()
    user_task.status = UserTask.Status.COMPLETED
    user_task.form_data = form_data or {}
    user_task.completed_at = timezone.now()
    user_task.completed_by = user
    user_task.save(
        update_fields=[
            "status",
            "form_data",
            "completed_at",
            "completed_by",
        ]
    )
    if user_task.activity_id:
        user_task.activity.status = ActivityInstance.Status.COMPLETED
        user_task.activity.completed_at = timezone.now()
        user_task.activity.save(update_fields=["status", "completed_at"])
    _advance(instance, workflow)
    return instance


def fire_timer(timer: ProcessTimer) -> None:
    from uuid import UUID

    if timer.fired:
        return
    instance = timer.instance
    if instance.status != ProcessInstance.Status.ACTIVE:
        timer.fired = True
        timer.save(update_fields=["fired"])
        return
    workflow = deserialize_workflow(instance.state_json)
    try:
        task = workflow.get_task_from_id(UUID(str(timer.spiff_task_id)))
    except Exception:  # noqa: BLE001
        task = None
    if task is not None and task.state == TaskState.WAITING:
        task.run()
    timer.fired = True
    timer.save(update_fields=["fired"])
    _advance(instance, workflow)


def _advance(instance: ProcessInstance, workflow: BpmnWorkflow) -> None:
    try:
        _run_engine_loop(instance, workflow)
        instance.state_json = serialize_workflow(workflow)
        instance.data = dict(workflow.data or {})
        if workflow.is_completed():
            instance.status = ProcessInstance.Status.COMPLETED
            instance.completed_at = timezone.now()
        instance.error_message = ""
        instance.save(
            update_fields=[
                "state_json",
                "data",
                "status",
                "completed_at",
                "error_message",
            ]
        )
        _sync_ready_tasks(instance, workflow)
        _publish(instance)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Process instance %s failed", instance.id)
        instance.status = ProcessInstance.Status.ERROR
        instance.error_message = str(exc)
        try:
            instance.state_json = serialize_workflow(workflow)
        except Exception:  # noqa: BLE001
            pass
        instance.save(update_fields=["status", "error_message", "state_json"])


def _run_engine_loop(instance: ProcessInstance, workflow: BpmnWorkflow) -> None:
    # Limit iterations to avoid infinite loops
    for _ in range(200):
        workflow.do_engine_steps()
        ready = list(workflow.get_tasks(state=TaskState.READY))
        started = list(workflow.get_tasks(state=TaskState.STARTED))
        service_tasks = [
            t
            for t in ready + started
            if isinstance(t.task_spec, ServiceTask)
        ]
        if not service_tasks:
            break
        for task in service_tasks:
            name = task.task_spec.name or getattr(task.task_spec, "bpmn_id", None) or "noop"
            bpmn_id = getattr(task.task_spec, "bpmn_id", None) or name
            activity = ActivityInstance.objects.create(
                instance=instance,
                task_id=str(task.id),
                task_name=task.task_spec.name or "",
                task_type="serviceTask",
                status=ActivityInstance.Status.ACTIVE,
                payload={"bpmn_id": bpmn_id, "operation": name},
            )
            result = run_service_task(instance, name, dict(task.data))
            task.data.update(result)
            workflow.data.update(result)
            if task.state == TaskState.READY:
                task.run()
            if task.state == TaskState.STARTED:
                task.complete()
            activity.status = ActivityInstance.Status.COMPLETED
            activity.completed_at = timezone.now()
            activity.payload = {**activity.payload, "result_keys": list(result.keys())}
            activity.save(update_fields=["status", "completed_at", "payload"])



def _sync_ready_tasks(instance: ProcessInstance, workflow: BpmnWorkflow) -> None:
    ready = list(workflow.get_tasks(state=TaskState.READY))
    existing_open = {
        t.spiff_task_id: t
        for t in instance.user_tasks.filter(status=UserTask.Status.OPEN)
    }
    seen = set()
    for task in ready:
        if not isinstance(task.task_spec, SpiffUserTask):
            # Timer / intermediate catch → schedule if waiting with duration in data
            continue
        tid = str(task.id)
        seen.add(tid)
        if tid in existing_open:
            continue
        activity = ActivityInstance.objects.create(
            instance=instance,
            task_id=tid,
            task_name=task.task_spec.name or "",
            task_type="userTask",
            status=ActivityInstance.Status.READY,
            payload={"bpmn_id": getattr(task.task_spec, "bpmn_id", "")},
        )
        form_schema = {}
        # extension: task data may carry form_schema
        if isinstance(task.data.get("form_schema"), dict):
            form_schema = task.data["form_schema"]
        due_hours = task.data.get("due_hours")
        due_at = None
        if due_hours is not None:
            try:
                due_at = timezone.now() + timedelta(hours=float(due_hours))
            except (TypeError, ValueError):
                due_at = None
        UserTask.objects.create(
            workspace=instance.workspace,
            instance=instance,
            activity=activity,
            spiff_task_id=tid,
            name=task.task_spec.name or task.task_spec.bpmn_id or "User task",
            candidate_role=str(task.data.get("candidate_role") or ""),
            form_schema=form_schema,
            assignee=instance.started_by if task.data.get("assign_starter") else None,
            due_at=due_at,
        )

    # Catch waiting timer events via IntermediateCatchEvent naming convention
    waiting = list(workflow.get_tasks(state=TaskState.WAITING))
    for task in waiting:
        delay_hours = task.data.get("timer_hours") or task.data.get("delay_hours")
        if delay_hours is None:
            continue
        tid = str(task.id)
        if ProcessTimer.objects.filter(
            instance=instance, spiff_task_id=tid, fired=False
        ).exists():
            continue
        try:
            hours = float(delay_hours)
        except (TypeError, ValueError):
            continue
        ProcessTimer.objects.create(
            instance=instance,
            spiff_task_id=tid,
            fire_at=timezone.now() + timedelta(hours=hours),
        )


def _publish(instance: ProcessInstance) -> None:
    try:
        from workspaces.events import publish_event
        from workspaces.webhooks import emit_webhook
        from audit.services import log_audit

        publish_event(
            instance.workspace_id,
            "process.updated",
            {
                "instance_id": instance.id,
                "status": instance.status,
            },
        )
        emit_webhook(
            instance.workspace,
            "process.updated",
            {"instance_id": instance.id, "status": instance.status},
        )
        log_audit(
            instance.workspace,
            instance.started_by,
            "update",
            "process_instance",
            entity_id=instance.id,
            summary=f"Process instance {instance.id} → {instance.status}",
        )
    except Exception:  # noqa: BLE001
        logger.debug("process publish side-effects failed", exc_info=True)
