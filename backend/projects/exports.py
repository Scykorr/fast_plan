"""CSV / XLSX / ICS export helpers for projects (WBS flatten + milestone calendars)."""

import csv
import io
from datetime import datetime

from django.http import HttpResponse
from django.utils import timezone

from projects.models import Project, ScheduleActivity

WBS_HEADERS = [
    "code",
    "title",
    "node_type",
    "assignee",
    "status",
    "progress",
    "start_date",
    "end_date",
]

XLSX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _flatten_wbs_rows(project: Project) -> list[dict]:
    nodes = (
        project.wbs_nodes.select_related("schedule", "assignee", "workflow_status")
        .order_by("position", "id")
    )
    rows = []
    for node in nodes:
        schedule = getattr(node, "schedule", None)
        rows.append(
            {
                "code": node.code,
                "title": node.title,
                "node_type": node.node_type,
                "assignee": node.assignee.email if node.assignee else "",
                "status": node.workflow_status.name if node.workflow_status else "",
                "progress": schedule.progress if schedule else "",
                "start_date": schedule.start_date.isoformat()
                if schedule and schedule.start_date
                else "",
                "end_date": schedule.end_date.isoformat()
                if schedule and schedule.end_date
                else "",
            }
        )
    return rows


def render_wbs_csv(project: Project) -> HttpResponse:
    rows = _flatten_wbs_rows(project)
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = (
        f'attachment; filename="project-{project.id}-wbs.csv"'
    )
    writer = csv.DictWriter(response, fieldnames=WBS_HEADERS)
    writer.writeheader()
    writer.writerows(rows)
    return response


def render_wbs_xlsx(project: Project) -> HttpResponse:
    import openpyxl

    rows = _flatten_wbs_rows(project)
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "WBS"
    sheet.append(WBS_HEADERS)
    for row in rows:
        sheet.append([row[header] for header in WBS_HEADERS])
    buffer = io.BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type=XLSX_CONTENT_TYPE)
    response["Content-Disposition"] = (
        f'attachment; filename="project-{project.id}-wbs.xlsx"'
    )
    return response


def _ics_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;").replace("\n", "\\n")


def _ics_date(value) -> str:
    if isinstance(value, datetime):
        return value.strftime("%Y%m%dT%H%M%SZ")
    return value.strftime("%Y%m%d")


def build_ics_calendar(events: list[dict], *, calendar_name: str) -> str:
    """events: [{"uid", "summary", "date" (date), "description"?}]"""
    now = timezone.now()
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Fast Plan//Milestones//RU",
        "CALSCALE:GREGORIAN",
        f"X-WR-CALNAME:{_ics_escape(calendar_name)}",
    ]
    for event in events:
        lines.append("BEGIN:VEVENT")
        lines.append(f"UID:{event['uid']}@fastplan")
        lines.append(f"DTSTAMP:{_ics_date(now)}")
        lines.append(f"DTSTART;VALUE=DATE:{_ics_date(event['date'])}")
        lines.append(f"SUMMARY:{_ics_escape(event['summary'])}")
        if event.get("description"):
            lines.append(f"DESCRIPTION:{_ics_escape(event['description'])}")
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines)


def render_ics_response(ics_text: str, filename: str) -> HttpResponse:
    response = HttpResponse(ics_text, content_type="text/calendar; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def project_milestones_ics(project: Project) -> HttpResponse:
    activities = (
        ScheduleActivity.objects.filter(
            wbs_node__project=project,
            is_milestone=True,
            start_date__isnull=False,
        )
        .select_related("wbs_node")
        .order_by("start_date", "id")
    )
    events = [
        {
            "uid": f"milestone-{activity.id}",
            "summary": f"{project.name}: {activity.wbs_node.title}",
            "date": activity.start_date,
            "description": f"WBS {activity.wbs_node.code}",
        }
        for activity in activities
    ]
    if project.end_date:
        events.append(
            {
                "uid": f"project-deadline-{project.id}",
                "summary": f"Дедлайн проекта: {project.name}",
                "date": project.end_date,
            }
        )
    ics_text = build_ics_calendar(events, calendar_name=f"{project.name} — вехи")
    return render_ics_response(ics_text, f"project-{project.id}-milestones.ics")


def workspace_calendar_ics(workspace) -> HttpResponse:
    activities = (
        ScheduleActivity.objects.filter(
            wbs_node__project__workspace=workspace,
            is_milestone=True,
            start_date__isnull=False,
        )
        .select_related("wbs_node", "wbs_node__project")
        .order_by("start_date", "id")
    )
    events = [
        {
            "uid": f"milestone-{activity.id}",
            "summary": f"{activity.wbs_node.project.name}: {activity.wbs_node.title}",
            "date": activity.start_date,
            "description": f"WBS {activity.wbs_node.code}",
        }
        for activity in activities
    ]
    projects_with_deadline = Project.objects.filter(
        workspace=workspace, end_date__isnull=False
    )
    for project in projects_with_deadline:
        events.append(
            {
                "uid": f"project-deadline-{project.id}",
                "summary": f"Дедлайн проекта: {project.name}",
                "date": project.end_date,
            }
        )
    ics_text = build_ics_calendar(events, calendar_name=f"{workspace.name} — вехи и дедлайны")
    return render_ics_response(ics_text, f"workspace-{workspace.id}-calendar.ics")
