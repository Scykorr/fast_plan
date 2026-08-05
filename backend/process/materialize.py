"""Materialize BPMN elements into ProcessWorkNode tree (Process-as-WBS)."""

from __future__ import annotations

from decimal import Decimal
import xml.etree.ElementTree as ET

from kanban.models import Card
from process.models import ProcessInstance, ProcessWorkNode, UserTask


def _local(tag: str) -> str:
    return tag.split("}", 1)[-1] if "}" in tag else tag


def _attr(el: ET.Element, name: str) -> str:
    return (el.attrib.get(name) or el.attrib.get(f"{{http://www.omg.org/spec/BPMN/20100524/MODEL}}{name}") or "").strip()


def _name(el: ET.Element) -> str:
    return _attr(el, "name") or _attr(el, "id") or "Element"


def _node_type(local: str) -> str:
    mapping = {
        "subProcess": ProcessWorkNode.NodeType.SUBPROCESS,
        "userTask": ProcessWorkNode.NodeType.USER_TASK,
        "serviceTask": ProcessWorkNode.NodeType.SERVICE_TASK,
        "scriptTask": ProcessWorkNode.NodeType.OTHER,
        "manualTask": ProcessWorkNode.NodeType.OTHER,
        "businessRuleTask": ProcessWorkNode.NodeType.OTHER,
        "callActivity": ProcessWorkNode.NodeType.OTHER,
        "task": ProcessWorkNode.NodeType.OTHER,
    }
    return mapping.get(local, ProcessWorkNode.NodeType.OTHER)


WORK_LOCALS = {
    "subProcess",
    "userTask",
    "serviceTask",
    "scriptTask",
    "manualTask",
    "businessRuleTask",
    "callActivity",
    "task",
}


def _find_process(root: ET.Element) -> ET.Element | None:
    for el in root.iter():
        if _local(el.tag) == "process":
            return el
    return None


def _fs_predecessors(process_el: ET.Element) -> dict[str, str]:
    """Map target bpmn_id → first incoming sequenceFlow source (FS predecessor)."""
    preds: dict[str, str] = {}
    for el in process_el.iter():
        if _local(el.tag) != "sequenceFlow":
            continue
        source = _attr(el, "sourceRef")
        target = _attr(el, "targetRef")
        if source and target and target not in preds:
            preds[target] = source
    return preds


def _walk(
    parent_el: ET.Element,
    *,
    instance: ProcessInstance,
    parent_node: ProcessWorkNode | None,
    counter: list[int],
    preds: dict[str, str],
    created: list[ProcessWorkNode],
) -> None:
    for child in list(parent_el):
        local = _local(child.tag)
        if local not in WORK_LOCALS:
            continue
        bpmn_id = _attr(child, "id")
        if not bpmn_id:
            continue
        counter[0] += 1
        node_type = _node_type(local)
        node = ProcessWorkNode.objects.create(
            workspace=instance.workspace,
            instance=instance,
            parent=parent_node,
            bpmn_id=bpmn_id,
            code=str(counter[0]),
            title=_name(child)[:255],
            node_type=node_type,
            position=counter[0],
            predecessor_bpmn_id=preds.get(bpmn_id, "")[:120],
            status=(
                ProcessWorkNode.Status.NA
                if node_type
                in (
                    ProcessWorkNode.NodeType.SUBPROCESS,
                    ProcessWorkNode.NodeType.OTHER,
                    ProcessWorkNode.NodeType.SERVICE_TASK,
                )
                else ProcessWorkNode.Status.OPEN
            ),
            progress=0,
        )
        created.append(node)
        if local == "subProcess":
            _walk(
                child,
                instance=instance,
                parent_node=node,
                counter=counter,
                preds=preds,
                created=created,
            )


def sync_work_nodes_with_tasks(instance: ProcessInstance) -> int:
    """Link open/completed UserTasks by bpmn_id in activity payload; update status/progress."""
    nodes = {
        n.bpmn_id: n
        for n in ProcessWorkNode.objects.filter(instance=instance)
    }
    updated = 0
    tasks = UserTask.objects.filter(instance=instance).select_related("activity")
    for task in tasks:
        payload = (task.activity.payload if task.activity_id else {}) or {}
        bpmn_id = str(payload.get("bpmn_id") or "").strip()
        if not bpmn_id or bpmn_id not in nodes:
            # Fallback: match by name for simple diagrams
            match = next(
                (
                    n
                    for n in nodes.values()
                    if n.node_type == ProcessWorkNode.NodeType.USER_TASK
                    and n.title == task.name
                    and n.user_task_id is None
                ),
                None,
            )
            if match is None:
                continue
            node = match
        else:
            node = nodes[bpmn_id]
        fields = ["user_task", "updated_at"]
        node.user_task = task
        if task.assignee_id and not node.assignee_id:
            node.assignee_id = task.assignee_id
            fields.append("assignee")
        if task.status == UserTask.Status.COMPLETED:
            node.status = ProcessWorkNode.Status.DONE
            node.progress = 100
            fields.extend(["status", "progress"])
        elif task.status == UserTask.Status.CANCELLED:
            node.status = ProcessWorkNode.Status.CANCELLED
            fields.append("status")
        elif task.status == UserTask.Status.OPEN:
            node.status = ProcessWorkNode.Status.OPEN
            if node.progress < 100:
                node.progress = max(node.progress, 0)
            fields.extend(["status", "progress"])
        node.save(update_fields=list(dict.fromkeys(fields)))
        from process.work_kanban import sync_card_from_work_node

        sync_card_from_work_node(node)
        updated += 1
    return updated


def materialize_work_tree(instance: ProcessInstance, *, replace: bool = False) -> dict:
    """
    Build ProcessWorkNode hierarchy from deployment BPMN.
    replace=True deletes existing nodes for this instance first.
    """
    if replace:
        ProcessWorkNode.objects.filter(instance=instance).delete()
    elif ProcessWorkNode.objects.filter(instance=instance).exists():
        sync_work_nodes_with_tasks(instance)
        from process.work_kanban import ensure_kanban_for_instance

        board = ensure_kanban_for_instance(instance)
        return {
            "created": 0,
            "synced": True,
            "board_id": board.id if board else None,
            "tree": build_work_tree(instance),
        }

    xml = instance.deployment.bpmn_xml or ""
    if not xml.strip():
        return {"created": 0, "synced": False, "tree": [], "detail": "empty bpmn"}

    root = ET.fromstring(xml)
    process_el = _find_process(root)
    if process_el is None:
        return {"created": 0, "synced": False, "tree": [], "detail": "no process"}

    preds = _fs_predecessors(process_el)
    counter = [0]
    created: list[ProcessWorkNode] = []

    # Synthetic root
    root_node = ProcessWorkNode.objects.create(
        workspace=instance.workspace,
        instance=instance,
        parent=None,
        bpmn_id=f"__root__{instance.id}",
        code="1",
        title=instance.deployment.definition.name
        if instance.deployment.definition_id
        else (instance.deployment.process_id or "Process"),
        node_type=ProcessWorkNode.NodeType.ROOT,
        position=0,
        status=ProcessWorkNode.Status.NA,
        progress=0,
    )
    created.append(root_node)
    counter[0] = 1

    _walk(
        process_el,
        instance=instance,
        parent_node=root_node,
        counter=counter,
        preds=preds,
        created=created,
    )
    sync_work_nodes_with_tasks(instance)
    from process.work_kanban import ensure_kanban_for_instance

    board = ensure_kanban_for_instance(instance)
    return {
        "created": len(created),
        "synced": True,
        "board_id": board.id if board else None,
        "tree": build_work_tree(instance),
    }


def build_work_tree(instance: ProcessInstance) -> list[dict]:
    from projects.capacity_hints import (
        assignee_week_loads,
        capacity_hint_for_assignee,
    )

    loads = assignee_week_loads(instance.workspace)
    nodes = list(
        ProcessWorkNode.objects.filter(instance=instance)
        .select_related(
            "assignee",
            "user_task",
            "card",
            "card__column",
            "card__column__board",
        )
        .prefetch_related("attachments", "time_entries")
        .order_by("position", "id")
    )
    by_parent: dict[int | None, list] = {}
    for n in nodes:
        by_parent.setdefault(n.parent_id, []).append(n)

    def serialize(n: ProcessWorkNode) -> dict:
        try:
            card = n.card
        except Card.DoesNotExist:
            card = None
        hours = Decimal("0")
        for entry in n.time_entries.all():
            hours += entry.hours
        return {
            "id": n.id,
            "parent_id": n.parent_id,
            "bpmn_id": n.bpmn_id,
            "code": n.code,
            "title": n.title,
            "description": n.description,
            "node_type": n.node_type,
            "position": n.position,
            "progress": n.progress,
            "status": n.status,
            "start_date": n.start_date.isoformat() if n.start_date else None,
            "end_date": n.end_date.isoformat() if n.end_date else None,
            "duration_days": n.duration_days,
            "assignee_id": n.assignee_id,
            "assignee_name": (
                n.assignee.get_full_name() or n.assignee.email
                if n.assignee_id
                else None
            ),
            "raci_r": n.raci_r,
            "raci_a": n.raci_a,
            "raci_c": n.raci_c,
            "raci_i": n.raci_i,
            "predecessor_bpmn_id": n.predecessor_bpmn_id,
            "user_task_id": n.user_task_id,
            "card_id": card.id if card is not None else None,
            "board_id": (
                card.column.board_id if card is not None else None
            ),
            "kanban_column": card.column.title if card is not None else None,
            "attachment_count": len(n.attachments.all()),
            "time_hours": str(hours),
            "capacity_hint": capacity_hint_for_assignee(loads, n.assignee_id),
            "children": [serialize(c) for c in by_parent.get(n.id, [])],
        }

    return [serialize(n) for n in by_parent.get(None, [])]
