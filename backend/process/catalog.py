"""Static service-adapter catalog for BPMN service tasks."""

from __future__ import annotations

from process.adapters import run_service_task  # noqa: F401 — keep import side for discoverability

ADAPTER_CATALOG = [
    {
        "operation": "noop",
        "label": "No-op",
        "description": "Pass-through; useful as a placeholder ServiceTask.",
        "params": [],
    },
    {
        "operation": "create_activity",
        "label": "Create CRM activity",
        "description": "Creates a CRM Activity linked to process org/deal/project.",
        "params": [
            {"name": "subject", "type": "string", "required": False},
            {"name": "body", "type": "string", "required": False},
            {"name": "kind", "type": "string", "required": False},
            {"name": "person_id", "type": "integer", "required": False},
        ],
    },
    {
        "operation": "create_deal_task",
        "label": "Create deal task",
        "description": "Creates a DealTask on instance.deal.",
        "params": [
            {"name": "title", "type": "string", "required": False},
            {"name": "notes", "type": "string", "required": False},
        ],
    },
    {
        "operation": "notify",
        "label": "Notify starter",
        "description": "In-app notification to process started_by.",
        "params": [
            {"name": "title", "type": "string", "required": False},
            {"name": "message", "type": "string", "required": False},
            {"name": "link", "type": "string", "required": False},
        ],
    },
    {
        "operation": "webhook",
        "label": "Workspace webhook",
        "description": "Emits process.service webhook with optional payload.",
        "params": [{"name": "payload", "type": "object", "required": False}],
    },
    {
        "operation": "evaluate_dmn",
        "label": "Evaluate DMN",
        "description": "Runs a DecisionDefinition by key and merges outputs into data.",
        "params": [
            {"name": "decision_key", "type": "string", "required": True},
            {"name": "inputs", "type": "object", "required": False},
            {"name": "output_map", "type": "object", "required": False},
        ],
    },
    {
        "operation": "create_wbs_note",
        "label": "Create WBS comment",
        "description": "Adds a work-item comment on a WBS node (project required).",
        "params": [
            {"name": "wbs_node_id", "type": "integer", "required": True},
            {"name": "body", "type": "string", "required": False},
        ],
    },
]

EXECUTABLE_ELEMENTS = [
    {"type": "startEvent", "status": "supported"},
    {"type": "endEvent", "status": "supported"},
    {"type": "userTask", "status": "supported"},
    {"type": "serviceTask", "status": "supported", "note": "See adapter catalog"},
    {"type": "exclusiveGateway", "status": "supported"},
    {"type": "parallelGateway", "status": "supported"},
    {
        "type": "inclusiveGateway",
        "status": "experimental",
        "note": "Executed by Spiff when present; no Fast Plan-specific UI yet",
    },
    {
        "type": "intermediateCatchEvent/timer",
        "status": "supported",
        "note": "Uses Celery ProcessTimer; set data.timer_hours or delay_hours",
    },
    {
        "type": "subProcess",
        "status": "planned",
        "note": "XML stored; nested instance lifecycle not implemented",
    },
]


def list_adapter_catalog() -> dict:
    return {
        "adapters": ADAPTER_CATALOG,
        "executable_elements": EXECUTABLE_ELEMENTS,
        "dispatch_hint": "Set ServiceTask name or data.operation to an adapter operation.",
    }
