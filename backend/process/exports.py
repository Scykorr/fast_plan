"""CSV / XLSX export for ProcessWorkNode trees."""

from __future__ import annotations

import csv
import io
from decimal import Decimal

from django.http import HttpResponse

from process.models import ProcessInstance, ProcessWorkNode
from projects.exports import XLSX_CONTENT_TYPE

PROCESS_WORK_HEADERS = [
    "code",
    "title",
    "node_type",
    "status",
    "progress",
    "assignee",
    "start_date",
    "end_date",
    "duration_days",
    "raci_r",
    "raci_a",
    "raci_c",
    "raci_i",
    "bpmn_id",
    "time_hours",
]


def _flatten_process_work_rows(instance: ProcessInstance) -> list[dict]:
    nodes = (
        ProcessWorkNode.objects.filter(instance=instance)
        .select_related("assignee")
        .prefetch_related("time_entries")
        .order_by("position", "id")
    )
    rows = []
    for node in nodes:
        hours = Decimal("0")
        for entry in node.time_entries.all():
            hours += entry.hours
        rows.append(
            {
                "code": node.code,
                "title": node.title,
                "node_type": node.node_type,
                "status": node.status,
                "progress": node.progress,
                "assignee": (
                    node.assignee.get_full_name() or node.assignee.email
                    if node.assignee_id
                    else ""
                ),
                "start_date": node.start_date.isoformat() if node.start_date else "",
                "end_date": node.end_date.isoformat() if node.end_date else "",
                "duration_days": node.duration_days,
                "raci_r": node.raci_r,
                "raci_a": node.raci_a,
                "raci_c": node.raci_c,
                "raci_i": node.raci_i,
                "bpmn_id": node.bpmn_id,
                "time_hours": str(hours),
            }
        )
    return rows


def render_process_work_csv(instance: ProcessInstance) -> HttpResponse:
    rows = _flatten_process_work_rows(instance)
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = (
        f'attachment; filename="process-{instance.id}-work-tree.csv"'
    )
    writer = csv.DictWriter(response, fieldnames=PROCESS_WORK_HEADERS)
    writer.writeheader()
    writer.writerows(rows)
    return response


def render_process_work_xlsx(instance: ProcessInstance) -> HttpResponse:
    import openpyxl

    rows = _flatten_process_work_rows(instance)
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "WorkTree"
    sheet.append(PROCESS_WORK_HEADERS)
    for row in rows:
        sheet.append([row[header] for header in PROCESS_WORK_HEADERS])
    buffer = io.BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type=XLSX_CONTENT_TYPE)
    response["Content-Disposition"] = (
        f'attachment; filename="process-{instance.id}-work-tree.xlsx"'
    )
    return response
