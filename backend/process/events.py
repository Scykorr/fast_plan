"""Domain event bridge: CRM/PM events → message-start process instances."""

from __future__ import annotations

import logging

logger = logging.getLogger("fast_plan")

# Map domain events to BPMN message / start hints stored on definition.category
# or definition key prefixes. For MVP we start published definitions whose
# category equals the event name (e.g. category="deal.created").


def dispatch_domain_event(workspace, event_name: str, payload: dict | None = None):
    """
    Start all published process definitions tagged with category=event_name.
    Also keeps P6e automations independent (called separately from views).
    """
    from process.models import ProcessDefinition, ProcessInstance
    from process.engine import start_instance
    from process.services import deploy_if_needed

    payload = payload or {}
    defs = ProcessDefinition.objects.filter(
        workspace=workspace,
        is_published=True,
        category=event_name,
    )
    started = []
    for definition in defs:
        try:
            deployment = deploy_if_needed(definition, user=None)
            instance = ProcessInstance.objects.create(
                workspace=workspace,
                deployment=deployment,
                business_key=str(payload.get("business_key") or ""),
                deal_id=payload.get("deal_id"),
                project_id=payload.get("project_id"),
                organization_id=payload.get("organization_id"),
                data={**payload, "event": event_name},
                started_by_id=payload.get("user_id"),
            )
            start_instance(instance)
            started.append(instance.id)
        except Exception:  # noqa: BLE001
            logger.exception(
                "Failed starting process %s for event %s", definition.key, event_name
            )
    return started
