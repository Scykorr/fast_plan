"""CSV import helpers mirroring export column layouts."""

import csv
import io
from datetime import date

from django.contrib.auth import get_user_model
from django.db import transaction

from projects.exports import WBS_HEADERS
from projects.models import ScheduleActivity, WBSNode
from projects.services import create_work_package

User = get_user_model()


def _parse_date(value: str):
    value = (value or "").strip()
    if not value:
        return None
    return date.fromisoformat(value)


def _decode_csv(raw: bytes) -> list[dict]:
    text = raw.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValueError("CSV file is empty.")
    missing = [header for header in ("code", "title") if header not in reader.fieldnames]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")
    return [dict(row) for row in reader]


@transaction.atomic
def import_wbs_csv(project, raw: bytes) -> dict:
    rows = _decode_csv(raw)
    root = project.wbs_nodes.filter(parent__isnull=True).order_by("id").first()
    if root is None:
        raise ValueError("Project has no root WBS node.")

    by_code = {root.code: root}
    created = 0
    updated = 0
    errors: list[str] = []

    # Parents should appear before children when codes are hierarchical.
    rows = sorted(rows, key=lambda row: (row.get("code") or "").count("."))

    for index, row in enumerate(rows, start=2):
        code = (row.get("code") or "").strip()
        title = (row.get("title") or "").strip()
        if not code or not title:
            errors.append(f"Row {index}: code and title are required.")
            continue
        if code == root.code:
            root.title = title
            root.save(update_fields=["title"])
            updated += 1
            continue

        parent_code = code.rsplit(".", 1)[0] if "." in code else root.code
        parent = by_code.get(parent_code) or project.wbs_nodes.filter(code=parent_code).first()
        if parent is None:
            errors.append(f"Row {index}: parent code {parent_code} not found for {code}.")
            continue

        node_type = (row.get("node_type") or WBSNode.NodeType.WORK_PACKAGE).strip()
        if node_type not in WBSNode.NodeType.values:
            node_type = WBSNode.NodeType.WORK_PACKAGE

        node = project.wbs_nodes.filter(code=code).first()
        if node is None:
            node = create_work_package(
                project,
                parent,
                title,
                node_type,
                with_schedule=True,
                with_kanban_card=node_type == WBSNode.NodeType.WORK_PACKAGE,
            )
            if node.code != code:
                node.code = code
                node.save(update_fields=["code"])
            created += 1
        else:
            node.title = title
            node.node_type = node_type
            node.parent = parent
            node.save(update_fields=["title", "node_type", "parent"])
            updated += 1

        by_code[code] = node

        assignee_email = (row.get("assignee") or "").strip()
        if assignee_email:
            user = User.objects.filter(
                email__iexact=assignee_email,
                workspace_memberships__workspace=project.workspace,
            ).first()
            if user:
                node.assignee = user
                node.save(update_fields=["assignee"])

        schedule, _ = ScheduleActivity.objects.get_or_create(
            wbs_node=node,
            defaults={
                "duration_days": 1,
                "progress": 0,
                "is_milestone": node_type == WBSNode.NodeType.MILESTONE,
            },
        )
        progress_raw = (row.get("progress") or "").strip()
        if progress_raw:
            try:
                schedule.progress = max(0, min(100, int(float(progress_raw))))
            except ValueError:
                errors.append(f"Row {index}: invalid progress '{progress_raw}'.")
        start = _parse_date(row.get("start_date", ""))
        end = _parse_date(row.get("end_date", ""))
        if start:
            schedule.start_date = start
        if end:
            schedule.end_date = end
        if start and end and end >= start:
            schedule.duration_days = max((end - start).days, 1)
        schedule.is_milestone = node_type == WBSNode.NodeType.MILESTONE
        schedule.save()

    return {
        "created": created,
        "updated": updated,
        "errors": errors,
        "headers": WBS_HEADERS,
    }
