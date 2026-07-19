import re
from datetime import date, timedelta
from collections import defaultdict

from django.db import IntegrityError

from birthdays.models import Contact
from birthdays.services import days_until_birthday
from kanban.models import Card
from notifications.mail import absolute_frontend_url, send_app_email
from notifications.models import Notification
from projects.models import Project, ScheduleActivity
from workspaces.models import Workspace, WorkspaceMember

MENTION_RE = re.compile(r"@(\w+)")


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


def notify_new_comment(comment) -> list[Notification]:
    """Notify the assignee and any @username mentions about a new comment."""
    workspace = comment.workspace
    author = comment.author
    created: list[Notification] = []

    if comment.wbs_node_id:
        node = comment.wbs_node
        project = node.project
        link = project_deep_link(project, tab="wbs", node=node.id)
        target_title = node.title
        assignee = node.assignee
    else:
        card = comment.card
        node = card.wbs_node
        project = card.column.board.project
        if project:
            link = project_deep_link(project, tab="kanban", card=card.id)
        else:
            link = f"/kanban?workspace={workspace.id}&card={card.id}"
        target_title = card.title
        assignee = node.assignee if node else None

    notified_user_ids: set[int] = {author.id}

    if assignee and assignee.id not in notified_user_ids:
        notification, was_created = create_notification(
            user=assignee,
            workspace=workspace,
            notification_type=Notification.NotificationType.COMMENT,
            title=f"Новый комментарий: {target_title}",
            message=comment.body[:200],
            link=link,
            dedupe_key=f"comment:{comment.id}:assignee:{assignee.id}",
        )
        notified_user_ids.add(assignee.id)
        if was_created:
            created.append(notification)

    usernames = set(MENTION_RE.findall(comment.body))
    if usernames:
        members = WorkspaceMember.objects.filter(
            workspace=workspace,
            user__username__in=usernames,
        ).select_related("user")
        for member in members:
            mentioned = member.user
            if mentioned.id in notified_user_ids:
                continue
            notification, was_created = create_notification(
                user=mentioned,
                workspace=workspace,
                notification_type=Notification.NotificationType.MENTION,
                title=f"Вас упомянули: {target_title}",
                message=comment.body[:200],
                link=link,
                dedupe_key=f"comment:{comment.id}:mention:{mentioned.id}",
            )
            notified_user_ids.add(mentioned.id)
            if was_created:
                created.append(notification)

    return created


def send_birthday_reminders(*, today: date | None = None) -> tuple[int, list]:
    today = today or date.today()
    created = 0
    created_items: list[Notification] = []
    for contact in Contact.objects.select_related("birthday", "workspace").all():
        days = days_until_birthday(contact.birthday.birth_date, today)
        if days > 7:
            continue
        dedupe = f"birthday:{contact.workspace_id}:{contact.id}:{today.isoformat()}"
        link = f"/calendar?workspace={contact.workspace_id}"
        for membership in _workspace_members(contact.workspace):
            notification, was_created = create_notification(
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
                created_items.append(notification)
    return created, created_items


def send_milestone_reminders(*, today: date | None = None) -> tuple[int, list]:
    today = today or date.today()
    horizon = today + timedelta(days=7)
    created = 0
    created_items: list[Notification] = []
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
            notification, was_created = create_notification(
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
                created_items.append(notification)
    return created, created_items


def send_deadline_reminders(*, today: date | None = None) -> tuple[int, list]:
    today = today or date.today()
    horizon = today + timedelta(days=7)
    created = 0
    created_items: list[Notification] = []

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
            notification, was_created = create_notification(
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
                created_items.append(notification)

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
            notification, was_created = create_notification(
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
                created_items.append(notification)

    projects = Project.objects.filter(
        end_date__gte=today,
        end_date__lte=horizon,
    ).select_related("workspace")
    for project in projects:
        dedupe = f"deadline:project:{project.id}:{project.end_date.isoformat()}"
        link = project_deep_link(project, tab="overview")
        for membership in _workspace_members(project.workspace):
            notification, was_created = create_notification(
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
                created_items.append(notification)

    return created, created_items


def send_reminder_digest_emails(
    created_items: list[Notification],
    *,
    today: date | None = None,
) -> int:
    """Send at most one digest email per user per day for newly created reminders."""
    from django.core.cache import cache

    today = today or date.today()
    if not created_items:
        return 0

    by_user: dict[int, list[Notification]] = defaultdict(list)
    for notification in created_items:
        by_user[notification.user_id].append(notification)

    sent = 0
    for user_id, items in by_user.items():
        user = items[0].user
        if not user.email:
            continue
        cache_key = f"email-digest:{user_id}:{today.isoformat()}"
        if cache.get(cache_key):
            continue

        payload = [
            {
                "title": item.title,
                "message": item.message,
                "url": absolute_frontend_url(item.link) if item.link else "",
            }
            for item in items
        ]
        if not payload:
            continue

        ok = send_app_email(
            to=user.email,
            subject=f"Напоминания Fast Plan — {today.isoformat()}",
            template_base="email/reminder_digest",
            context={
                "digest_date": today.isoformat(),
                "items": payload,
            },
        )
        if ok:
            cache.set(cache_key, True, timeout=60 * 60 * 36)
            sent += 1
    return sent


def run_all_reminders(*, today: date | None = None) -> dict[str, int]:
    today = today or date.today()
    birthdays, birthday_items = send_birthday_reminders(today=today)
    milestones, milestone_items = send_milestone_reminders(today=today)
    deadlines, deadline_items = send_deadline_reminders(today=today)
    created_items = birthday_items + milestone_items + deadline_items
    emails = send_reminder_digest_emails(created_items, today=today)
    return {
        "birthdays": birthdays,
        "milestones": milestones,
        "deadlines": deadlines,
        "emails": emails,
        "workspaces": Workspace.objects.count(),
    }
