"""CMMN-lite plan item helpers (P8d + P8g richer cases)."""

from __future__ import annotations

from typing import Any


def normalize_plan_item(item: dict) -> dict[str, Any]:
    return {
        "id": str(item.get("id") or ""),
        "name": str(item.get("name") or item.get("id") or ""),
        "discretionary": bool(item.get("discretionary")),
        "required": bool(item.get("required", not item.get("discretionary"))),
        "depends_on": [str(x) for x in (item.get("depends_on") or [])],
        "process_key": str(item.get("process_key") or ""),
    }


def plan_items(definition) -> list[dict[str, Any]]:
    return [normalize_plan_item(i) for i in (definition.plan_items or []) if i]


def find_plan_item(definition, item_id: str) -> dict[str, Any] | None:
    for item in plan_items(definition):
        if item["id"] == item_id:
            return item
    return None


def available_items(case) -> list[dict[str, Any]]:
    """Plan items that can be completed now (deps satisfied, not yet done)."""
    completed = set(case.completed_items or [])
    out: list[dict[str, Any]] = []
    for item in plan_items(case.definition):
        if not item["id"] or item["id"] in completed:
            continue
        if not all(dep in completed for dep in item["depends_on"]):
            continue
        out.append({**item, "enabled": True})
    return out


def required_incomplete(case) -> list[str]:
    completed = set(case.completed_items or [])
    return [
        item["id"]
        for item in plan_items(case.definition)
        if item["required"] and item["id"] and item["id"] not in completed
    ]


def is_item_available(case, item_id: str) -> bool:
    return any(i["id"] == item_id for i in available_items(case))
