"""Service-task adapters invoked from BPMN service tasks by name/operation."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("fast_plan")


def run_service_task(instance, task_name: str, data: dict[str, Any]) -> dict[str, Any]:
    """
    Dispatch a service task.

    Convention: task name or data['operation'] selects the adapter:
      create_activity, create_deal_task, notify, webhook, evaluate_dmn, noop
    """
    operation = (data.get("operation") or task_name or "noop").strip().lower()
    handlers = {
        "create_activity": _create_activity,
        "create_deal_task": _create_deal_task,
        "notify": _notify,
        "webhook": _webhook,
        "evaluate_dmn": _evaluate_dmn,
        "noop": _noop,
        "servicetask": _noop,
    }
    handler = handlers.get(operation, _noop)
    result = handler(instance, data)
    data.update(result or {})
    return data


def _noop(instance, data):
    return {"service_result": "noop"}


def _create_activity(instance, data):
    from crm.models import Activity

    if not instance.organization_id and not data.get("person_id"):
        return {"service_error": "organization or person required"}
    activity = Activity.objects.create(
        workspace=instance.workspace,
        kind=data.get("kind") or Activity.Kind.NOTE,
        subject=data.get("subject") or f"Process {instance.id}",
        body=data.get("body") or "",
        organization_id=instance.organization_id or data.get("organization_id"),
        person_id=data.get("person_id"),
        deal_id=instance.deal_id or data.get("deal_id"),
        project_id=instance.project_id or data.get("project_id"),
        created_by=instance.started_by,
    )
    return {"activity_id": activity.id}


def _create_deal_task(instance, data):
    from crm.models import DealTask

    if not instance.deal_id:
        return {"service_error": "deal required"}
    task = DealTask.objects.create(
        deal_id=instance.deal_id,
        title=data.get("title") or f"Process task {instance.id}",
        notes=data.get("notes") or "",
        assignee=instance.started_by,
    )
    return {"deal_task_id": task.id}


def _notify(instance, data):
    from notifications.services import create_notification
    from notifications.models import Notification

    user = instance.started_by
    if user is None:
        return {"service_error": "no user"}
    create_notification(
        user=user,
        notification_type=Notification.NotificationType.DEADLINE,
        title=data.get("title") or f"Process {instance.id}",
        message=data.get("message") or "",
        link=data.get("link") or f"/processes/instances/{instance.id}",
        workspace=instance.workspace,
    )
    return {"notified": True}


def _webhook(instance, data):
    from workspaces.webhooks import emit_webhook

    emit_webhook(
        instance.workspace,
        "process.service",
        {
            "instance_id": instance.id,
            "payload": data.get("payload") or {},
        },
    )
    return {"webhook": True}


def _evaluate_dmn(instance, data):
    from process.dmn import evaluate_decision

    key = data.get("decision_key") or ""
    if not key:
        return {"service_error": "decision_key required"}
    result = evaluate_decision(
        workspace=instance.workspace,
        decision_key=key,
        inputs=data.get("inputs") or instance.data,
    )
    out = {"dmn_result": result}
    output_map = data.get("output_map")
    if isinstance(output_map, dict) and isinstance(result, dict):
        mapped = {}
        for target, source in output_map.items():
            if source in result:
                mapped[str(target)] = result[source]
                instance.data[str(target)] = result[source]
        out["dmn_mapped"] = mapped
    elif isinstance(result, dict):
        # Default: merge non-meta keys into instance data
        for k, v in result.items():
            if k in ("matched", "hit_policy", "matched_unique", "all_matches", "inputs"):
                continue
            instance.data[k] = v
    return out
