from django.core.exceptions import ObjectDoesNotExist
from datetime import date, timedelta

from django.db.models import Q, Sum

from birthdays.models import Contact
from kanban.models import Card
from projects.models import Project, Risk, ScheduleActivity, WBSNode
from timelog.models import TimeEntry
from workspaces.models import MemberCapacity, WorkspaceMember


def _user_label(user):
    if user is None:
        return None
    return user.get_full_name() or user.email


def _project_link(project_id, workspace_id, **params):
    query = [f"workspace={workspace_id}"]
    for key, value in params.items():
        if value is not None:
            query.append(f"{key}={value}")
    return f"/projects/{project_id}?{'&'.join(query)}"


def search_workspace(workspace, query: str, *, types=None, limit=20):
    q = (query or "").strip()
    if len(q) < 2:
        return {"workspace_id": workspace.id, "query": q, "results": []}

    allowed = {"project", "wbs", "card", "risk", "contact"}
    selected = set(types or allowed) & allowed
    results = []

    if "project" in selected:
        for project in Project.objects.filter(workspace=workspace).filter(
            Q(name__icontains=q) | Q(description__icontains=q)
        )[:limit]:
            results.append(
                {
                    "type": "project",
                    "id": project.id,
                    "title": project.name,
                    "subtitle": project.status,
                    "project_id": project.id,
                    "project_name": project.name,
                    "link": _project_link(project.id, workspace.id, tab="overview"),
                    "extra": {},
                }
            )

    if "wbs" in selected:
        nodes = (
            WBSNode.objects.filter(project__workspace=workspace)
            .filter(Q(title__icontains=q) | Q(code__icontains=q) | Q(description__icontains=q))
            .select_related("project", "assignee", "workflow_status")[:limit]
        )
        for node in nodes:
            try:
                card_id = node.card.id
            except ObjectDoesNotExist:
                card_id = None
            results.append(
                {
                    "type": "wbs",
                    "id": node.id,
                    "title": f"{node.code} {node.title}",
                    "subtitle": f"{node.project.name} / {_user_label(node.assignee) or '—'}",
                    "project_id": node.project_id,
                    "project_name": node.project.name,
                    "link": _project_link(
                        node.project_id,
                        workspace.id,
                        tab="wbs",
                        node=node.id,
                    ),
                    "extra": {
                        "wbs_code": node.code,
                        "assignee_id": node.assignee_id,
                        "assignee_name": _user_label(node.assignee),
                        "card_id": card_id,
                        "workflow_status_id": node.workflow_status_id,
                        "workflow_status_name": (
                            node.workflow_status.name if node.workflow_status else None
                        ),
                    },
                }
            )

    if "card" in selected:
        cards = (
            Card.objects.filter(column__board__workspace=workspace)
            .filter(Q(title__icontains=q) | Q(description__icontains=q))
            .select_related("column__board__project", "wbs_node")[:limit]
        )
        for card in cards:
            project = card.column.board.project
            link = (
                _project_link(project.id, workspace.id, tab="kanban", card=card.id)
                if project
                else f"/kanban?workspace={workspace.id}&card={card.id}"
            )
            results.append(
                {
                    "type": "card",
                    "id": card.id,
                    "title": card.title,
                    "subtitle": project.name if project else card.column.board.title,
                    "project_id": project.id if project else None,
                    "project_name": project.name if project else None,
                    "link": link,
                    "extra": {"board_id": card.column.board_id},
                }
            )

    if "risk" in selected:
        risks = (
            Risk.objects.filter(project__workspace=workspace)
            .filter(Q(title__icontains=q) | Q(description__icontains=q))
            .select_related("project")[:limit]
        )
        for risk in risks:
            results.append(
                {
                    "type": "risk",
                    "id": risk.id,
                    "title": risk.title,
                    "subtitle": f"{risk.project.name} · score {risk.score}",
                    "project_id": risk.project_id,
                    "project_name": risk.project.name,
                    "link": _project_link(
                        risk.project_id,
                        workspace.id,
                        tab="risks",
                        risk=risk.id,
                    ),
                    "extra": {"score": risk.score, "status": risk.status},
                }
            )

    if "contact" in selected:
        contacts = Contact.objects.filter(workspace=workspace, name__icontains=q)[:limit]
        for contact in contacts:
            results.append(
                {
                    "type": "contact",
                    "id": contact.id,
                    "title": contact.name,
                    "subtitle": contact.relation,
                    "project_id": None,
                    "project_name": None,
                    "link": f"/calendar?workspace={workspace.id}",
                    "extra": {},
                }
            )

    return {
        "workspace_id": workspace.id,
        "query": q,
        "results": results[:limit],
    }


def list_my_tasks(
    workspace,
    assignee,
    *,
    include_done=False,
    overdue_only=False,
    limit=50,
):
    today = date.today()
    nodes = (
        WBSNode.objects.filter(project__workspace=workspace, assignee=assignee)
        .select_related(
            "project",
            "assignee",
            "workflow_status",
            "schedule",
        )
        .order_by("id")
    )
    tasks = []
    overdue = 0
    due_soon = 0
    for node in nodes:
        schedule = getattr(node, "schedule", None)
        progress = schedule.progress if schedule else 0
        if not include_done and progress >= 100:
            continue
        end_date = schedule.end_date if schedule else None
        days_overdue = (
            (today - end_date).days
            if end_date and end_date < today and progress < 100
            else 0
        )
        if days_overdue > 0:
            overdue += 1
        elif (
            end_date
            and today <= end_date <= today + timedelta(days=7)
            and progress < 100
        ):
            due_soon += 1
        if overdue_only and days_overdue <= 0:
            continue
        try:
            card = node.card
            card_id = card.id
            board_id = card.column.board_id
        except ObjectDoesNotExist:
            card_id = None
            board_id = None
        tasks.append(
            {
                "wbs_id": node.id,
                "wbs_code": node.code,
                "title": node.title,
                "node_type": node.node_type,
                "project_id": node.project_id,
                "project_name": node.project.name,
                "assignee_id": node.assignee_id,
                "assignee_name": _user_label(node.assignee),
                "workflow_status_id": node.workflow_status_id,
                "workflow_status_name": (
                    node.workflow_status.name if node.workflow_status else None
                ),
                "progress": progress,
                "start_date": schedule.start_date.isoformat()
                if schedule and schedule.start_date
                else None,
                "end_date": end_date.isoformat() if end_date else None,
                "days_overdue": days_overdue,
                "card_id": card_id,
                "board_id": board_id,
                "link": _project_link(
                    node.project_id,
                    workspace.id,
                    tab="wbs",
                    node=node.id,
                ),
            }
        )

    tasks.sort(
        key=lambda item: (
            0 if item["days_overdue"] > 0 else 1,
            item["end_date"] or "9999-12-31",
            item["wbs_id"],
        )
    )
    tasks = tasks[:limit]
    return {
        "workspace_id": workspace.id,
        "assignee_id": assignee.id,
        "assignee_name": _user_label(assignee),
        "summary": {
            "total": len(tasks),
            "overdue": overdue,
            "due_soon": due_soon,
        },
        "tasks": tasks,
    }


def _overlap_days(start: date | None, end: date | None, week_start: date, week_end: date) -> int:
    if not start or not end:
        return 0
    left = max(start, week_start)
    right = min(end, week_end)
    if right < left:
        return 0
    return (right - left).days + 1


def build_capacity_report(workspace, *, week_start: date | None = None):
    if week_start is None:
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    memberships = list(
        WorkspaceMember.objects.filter(workspace=workspace)
        .select_related("user")
        .order_by("user__email")
    )
    capacity_map = {
        item.user_id: item.hours_per_week
        for item in MemberCapacity.objects.filter(workspace=workspace)
    }

    activities = list(
        ScheduleActivity.objects.filter(
            wbs_node__project__workspace=workspace,
            wbs_node__assignee__isnull=False,
            progress__lt=100,
        )
        .filter(start_date__lte=week_end, end_date__gte=week_start)
        .select_related("wbs_node", "wbs_node__assignee", "wbs_node__project")
    )

    allocated: dict[int, float] = {}
    details: dict[int, list] = {}
    for activity in activities:
        node = activity.wbs_node
        user_id = node.assignee_id
        overlap = _overlap_days(activity.start_date, activity.end_date, week_start, week_end)
        if overlap <= 0:
            continue
        remaining_ratio = max(0.0, 1 - (activity.progress / 100))
        hours = round(overlap * 8 * remaining_ratio, 1)
        allocated[user_id] = allocated.get(user_id, 0) + hours
        details.setdefault(user_id, []).append(
            {
                "wbs_id": node.id,
                "title": node.title,
                "project_id": node.project_id,
                "project_name": node.project.name,
                "hours": hours,
                "overlap_days": overlap,
            }
        )

    logged = (
        TimeEntry.objects.filter(
            workspace=workspace,
            work_date__gte=week_start,
            work_date__lte=week_end,
        )
        .values("user_id")
        .annotate(total=Sum("hours"))
    )
    logged_map = {item["user_id"]: float(item["total"] or 0) for item in logged}

    members = []
    for membership in memberships:
        user = membership.user
        capacity_hours = capacity_map.get(user.id, 40)
        allocated_hours = round(allocated.get(user.id, 0), 1)
        members.append(
            {
                "user_id": user.id,
                "name": _user_label(user),
                "email": user.email,
                "role": membership.role,
                "capacity_hours": capacity_hours,
                "allocated_hours": allocated_hours,
                # Actual effort hint from logged time entries (see CHANGELOG) — not
                # yet blended into EVM actual cost/effort, shown alongside plan.
                "logged_hours": round(logged_map.get(user.id, 0), 1),
                "utilization": round(allocated_hours / capacity_hours, 2)
                if capacity_hours
                else None,
                "assignments": details.get(user.id, []),
            }
        )

    return {
        "workspace_id": workspace.id,
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat(),
        "members": members,
    }
