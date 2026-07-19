from datetime import date, timedelta

from django.db import IntegrityError

from birthdays.models import Contact
from birthdays.services import days_until_birthday
from kanban.models import Card
from notifications.models import Notification
from projects.models import Project, ScheduleActivity
from workspaces.models import Workspace, WorkspaceMember


def project_deep_link(project, *, tab=None, node=None, risk=None, card=None):
    params = [f"workspace={project.workspace_id}"]
    if tab:
        params.append(f"tab={tab}")
    if node:
        params.append(f"node={node}")
    if risk:
        params.append(f"risk={risk}")
    if card:
        params.append(f"card={card}")
    return f"/projects/{project.id}?{'&'.join(params)}"


def create_notification(
    *,
    user,
    notification_type,
    title,
    message="",
    link="",
    workspace=None,
    dedupe_key="",
):
    if dedupe_key:
        existing = Notification.objects.filter(user=user, dedupe_key=dedupe_key).first()
        if existing:
            return existing, False
    try:
        notification = Notification.objects.create(
            user=user,
            workspace=workspace,
            notification_type=notification_type,
            title=title,
            message=message,
            link=link,
            dedupe_key=dedupe_key,
        )
        return notification, True
    except IntegrityError:
        existing = Notification.objects.filter(user=user, dedupe_key=dedupe_key).first()
        return existing, False


def _workspace_members(workspace):
    return WorkspaceMember.objects.filter(workspace=workspace).select_related("user")


def send_birthday_reminders(*, today: date | None = None) -> int:
    today = today or date.today()
    created = 0
    for contact in Contact.objects.select_related("birthday", "workspace").all():
        days = days_until_birthday(contact.birthday.birth_date, today)
        if days > 7:
            continue
        dedupe = f"birthday:{contact.workspace_id}:{contact.id}:{today.isoformat()}"
        link = f"/calendar?workspace={contact.workspace_id}"
        for membership in _workspace_members(contact.workspace):
            _, was_created = create_notification(
                user=membership.user,
                workspace=contact.workspace,
                notification_type=Notification.NotificationType.BIRTHDAY,
                title=f"ДР: {contact.name}",
                message=f"Через {days} дн.",
                link=link,
                dedupe_key=dedupe,
            )
            if was_created:
                created += 1
    return created


def send_milestone_reminders(*, today: date | None = None) -> int:
    today = today or date.today()
    horizon = today + timedelta(days=7)
    created = 0
    activities = ScheduleActivity.objects.filter(
        is_milestone=True,
        start_date__gte=today,
        start_date__lte=horizon,
    ).select_related("wbs_node", "wbs_node__project", "wbs_node__project__workspace")
    for activity in activities:
        project = activity.wbs_node.project
        workspace = project.workspace
        dedupe = f"milestone:{activity.id}:{activity.start_date.isoformat()}"
        link = project_deep_link(project, tab="wbs", node=activity.wbs_node_id)
        for membership in _workspace_members(workspace):
            _, was_created = create_notification(
                user=membership.user,
                workspace=workspace,
                notification_type=Notification.NotificationType.MILESTONE,
                title=f"Веха: {activity.wbs_node.title}",
                message=f"Проект «{project.name}» — {activity.start_date}",
                link=link,
                dedupe_key=dedupe,
            )
            if was_created:
                created += 1
    return created


def send_deadline_reminders(*, today: date | None = None) -> int:
    today = today or date.today()
    horizon = today + timedelta(days=7)
    created = 0

    activities = ScheduleActivity.objects.filter(
        end_date__gte=today,
        end_date__lte=horizon,
        progress__lt=100,
        is_milestone=False,
    ).select_related("wbs_node", "wbs_node__project", "wbs_node__project__workspace")
    for activity in activities:
        project = activity.wbs_node.project
        dedupe = f"deadline:schedule:{activity.id}:{activity.end_date.isoformat()}"
        link = project_deep_link(project, tab="wbs", node=activity.wbs_node_id)
        for membership in _workspace_members(project.workspace):
            _, was_created = create_notification(
                user=membership.user,
                workspace=project.workspace,
                notification_type=Notification.NotificationType.DEADLINE,
                title=f"Дедлайн: {activity.wbs_node.title}",
                message=f"Проект «{project.name}» — до {activity.end_date}",
                link=link,
                dedupe_key=dedupe,
            )
            if was_created:
                created += 1

    cards = Card.objects.filter(
        due_date__gte=today,
        due_date__lte=horizon,
    ).select_related("column__board__workspace", "column__board__project")
    for card in cards:
        workspace = card.column.board.workspace
        project = card.column.board.project
        dedupe = f"deadline:card:{card.id}:{card.due_date.isoformat()}"
        if project:
            link = project_deep_link(project, tab="kanban", card=card.id)
        else:
            link = f"/kanban?workspace={workspace.id}&card={card.id}"
        for membership in _workspace_members(workspace):
            _, was_created = create_notification(
                user=membership.user,
                workspace=workspace,
                notification_type=Notification.NotificationType.DEADLINE,
                title=f"Дедлайн карточки: {card.title}",
                message=f"Срок {card.due_date}",
                link=link,
                dedupe_key=dedupe,
            )
            if was_created:
                created += 1

    projects = Project.objects.filter(
        end_date__gte=today,
        end_date__lte=horizon,
    ).select_related("workspace")
    for project in projects:
        dedupe = f"deadline:project:{project.id}:{project.end_date.isoformat()}"
        link = project_deep_link(project, tab="overview")
        for membership in _workspace_members(project.workspace):
            _, was_created = create_notification(
                user=membership.user,
                workspace=project.workspace,
                notification_type=Notification.NotificationType.DEADLINE,
                title=f"Дедлайн проекта: {project.name}",
                message=f"Окончание {project.end_date}",
                link=link,
                dedupe_key=dedupe,
            )
            if was_created:
                created += 1

    return created


def run_all_reminders(*, today: date | None = None) -> dict[str, int]:
    today = today or date.today()
    return {
        "birthdays": send_birthday_reminders(today=today),
        "milestones": send_milestone_reminders(today=today),
        "deadlines": send_deadline_reminders(today=today),
        "workspaces": Workspace.objects.count(),
    }
