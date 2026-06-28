from datetime import date

from projects.models import Project, ScheduleActivity


def milestone_date_in_month(activity: ScheduleActivity, year: int, month: int) -> date | None:
    if not activity.is_milestone or activity.start_date is None:
        return None
    if activity.start_date.year == year and activity.start_date.month == month:
        return activity.start_date
    return None


def serialize_milestone_event(activity: ScheduleActivity, project: Project) -> dict:
    return {
        "id": f"milestone-{activity.id}",
        "title": f"{project.name}: {activity.wbs_node.title}",
        "start": activity.start_date.isoformat(),
        "allDay": True,
        "extendedProps": {
            "activity_id": activity.id,
            "project_id": project.id,
            "project_name": project.name,
            "wbs_code": activity.wbs_node.code,
            "event_type": "milestone",
        },
    }


def project_milestone_events(project: Project, year: int, month: int) -> list[dict]:
    activities = (
        ScheduleActivity.objects.filter(
            wbs_node__project=project,
            is_milestone=True,
            start_date__isnull=False,
        )
        .select_related("wbs_node")
        .order_by("start_date", "id")
    )
    events = []
    for activity in activities:
        if milestone_date_in_month(activity, year, month) is not None:
            events.append(serialize_milestone_event(activity, project))
    return events


def workspace_milestone_events(workspace, year: int, month: int) -> list[dict]:
    activities = (
        ScheduleActivity.objects.filter(
            wbs_node__project__workspace=workspace,
            is_milestone=True,
            start_date__isnull=False,
        )
        .select_related("wbs_node", "wbs_node__project")
        .order_by("start_date", "id")
    )
    events = []
    for activity in activities:
        project = activity.wbs_node.project
        if milestone_date_in_month(activity, year, month) is not None:
            events.append(serialize_milestone_event(activity, project))
    return events
