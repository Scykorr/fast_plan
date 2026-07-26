"""Shared helpers for DealTask / LeadTask (priority, checklist, repeat, board)."""

from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta
from uuid import uuid4

from rest_framework.exceptions import ValidationError

from crm.models import DealTask, LeadTask

PRIORITY_VALUES = {c.value for c in DealTask.Priority}
BOARD_VALUES = {c.value for c in DealTask.BoardStatus}
REPEAT_VALUES = {c.value for c in DealTask.Repeat}


def normalize_checklist(raw) -> list[dict]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ValidationError({"checklist": "Must be a list of checklist items."})
    out: list[dict] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text") or "").strip()
        if not text:
            continue
        out.append(
            {
                "id": str(item.get("id") or uuid4()),
                "text": text[:255],
                "done": bool(item.get("done")),
            }
        )
    return out


def next_due_date(due: date | None, repeat: str) -> date | None:
    if repeat == DealTask.Repeat.NONE:
        return None
    base = due or date.today()
    if repeat == DealTask.Repeat.DAILY:
        return base + timedelta(days=1)
    if repeat == DealTask.Repeat.WEEKLY:
        return base + timedelta(weeks=1)
    if repeat == DealTask.Repeat.MONTHLY:
        year, month = base.year, base.month + 1
        if month > 12:
            year, month = year + 1, 1
        day = min(base.day, monthrange(year, month)[1])
        return date(year, month, day)
    return None


def reset_checklist(checklist: list | None) -> list[dict]:
    return [
        {"id": str(item.get("id") or uuid4()), "text": item["text"], "done": False}
        for item in (checklist or [])
        if isinstance(item, dict) and item.get("text")
    ]


def apply_task_fields(task, data: dict, *, request_data: dict) -> None:
    """Apply validated write fields onto DealTask or LeadTask."""
    was_done = bool(task.is_done)
    if "title" in request_data:
        task.title = data["title"]
    if "due_date" in request_data:
        task.due_date = data.get("due_date")
    if "remind_before_days" in data:
        task.remind_before_days = data["remind_before_days"]
    if "notes" in data:
        task.notes = data["notes"]
    if "priority" in data:
        task.priority = data["priority"]
    if "repeat" in data:
        task.repeat = data["repeat"]
    if "checklist" in request_data:
        task.checklist = normalize_checklist(request_data.get("checklist"))

    if "board_status" in request_data:
        status_value = data.get("board_status") or request_data["board_status"]
        if status_value not in BOARD_VALUES:
            raise ValidationError({"board_status": "Invalid board status."})
        task.board_status = status_value
        task.is_done = status_value == DealTask.BoardStatus.DONE
    elif "is_done" in data:
        task.is_done = data["is_done"]
        if task.is_done:
            task.board_status = DealTask.BoardStatus.DONE
        elif task.board_status == DealTask.BoardStatus.DONE:
            task.board_status = DealTask.BoardStatus.TODO

    task.save()

    if task.is_done and not was_done and task.repeat != DealTask.Repeat.NONE:
        spawn_repeat_occurrence(task)


def spawn_repeat_occurrence(task) -> DealTask | LeadTask | None:
    nxt = next_due_date(task.due_date, task.repeat)
    if nxt is None:
        return None
    fields = {
        "title": task.title,
        "due_date": nxt,
        "is_done": False,
        "priority": task.priority,
        "board_status": DealTask.BoardStatus.TODO,
        "checklist": reset_checklist(task.checklist),
        "repeat": task.repeat,
        "assignee": task.assignee,
        "remind_before_days": task.remind_before_days,
        "notes": task.notes,
    }
    if isinstance(task, DealTask):
        return DealTask.objects.create(deal=task.deal, **fields)
    if isinstance(task, LeadTask):
        return LeadTask.objects.create(lead=task.lead, **fields)
    return None


def board_item_from_deal_task(task: DealTask) -> dict:
    return {
        "kind": "deal",
        "id": task.id,
        "title": task.title,
        "due_date": task.due_date.isoformat() if task.due_date else None,
        "is_done": task.is_done,
        "priority": task.priority,
        "board_status": task.board_status,
        "checklist": task.checklist or [],
        "repeat": task.repeat,
        "assignee": task.assignee_id,
        "assignee_email": task.assignee.email if task.assignee_id else None,
        "deal_id": task.deal_id,
        "deal_title": task.deal.title,
        "lead_id": None,
        "lead_name": None,
        "remind_before_days": task.remind_before_days,
        "notes": task.notes,
        "created_at": task.created_at.isoformat().replace("+00:00", "Z"),
        "updated_at": task.updated_at.isoformat().replace("+00:00", "Z"),
    }


def board_item_from_lead_task(task: LeadTask) -> dict:
    return {
        "kind": "lead",
        "id": task.id,
        "title": task.title,
        "due_date": task.due_date.isoformat() if task.due_date else None,
        "is_done": task.is_done,
        "priority": task.priority,
        "board_status": task.board_status,
        "checklist": task.checklist or [],
        "repeat": task.repeat,
        "assignee": task.assignee_id,
        "assignee_email": task.assignee.email if task.assignee_id else None,
        "deal_id": None,
        "deal_title": None,
        "lead_id": task.lead_id,
        "lead_name": task.lead.full_name,
        "remind_before_days": task.remind_before_days,
        "notes": task.notes,
        "created_at": task.created_at.isoformat().replace("+00:00", "Z"),
        "updated_at": task.updated_at.isoformat().replace("+00:00", "Z"),
    }
