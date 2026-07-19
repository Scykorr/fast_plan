from datetime import date, timedelta

from django.db.models.signals import post_save
from django.dispatch import receiver

from birthdays.services import days_until_birthday
from notifications.models import Notification
from projects.models import Project, Risk, ScheduleActivity
from workspaces.models import WorkspaceMember


def create_notification(
    user,
    notification_type,
    title,
    message="",
    link="",
    workspace=None,
):
    Notification.objects.create(
        user=user,
        workspace=workspace,
        notification_type=notification_type,
        title=title,
        message=message,
        link=link,
    )


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


@receiver(post_save, sender=Risk)
def notify_high_risk(sender, instance, created, **kwargs):
    if not created or instance.score < 15:
        return
    project = instance.project
    members = WorkspaceMember.objects.filter(workspace=project.workspace).select_related(
        "user"
    )
    link = project_deep_link(project, tab="risks", risk=instance.id)
    for membership in members:
        create_notification(
            membership.user,
            Notification.NotificationType.RISK,
            f"Высокий риск: {instance.title}",
            f"Проект «{project.name}» — оценка {instance.score}",
            link,
            workspace=project.workspace,
        )


@receiver(post_save, sender=Project)
def notify_upcoming_milestones_on_create(sender, instance, created, **kwargs):
    if not created:
        return
    _check_milestone_reminders(instance.workspace)


def _check_milestone_reminders(workspace):
    today = date.today()
    horizon = today + timedelta(days=7)
    activities = ScheduleActivity.objects.filter(
        wbs_node__project__workspace=workspace,
        is_milestone=True,
        start_date__gte=today,
        start_date__lte=horizon,
    ).select_related("wbs_node", "wbs_node__project")
    members = WorkspaceMember.objects.filter(workspace=workspace).select_related("user")
    for activity in activities:
        project = activity.wbs_node.project
        link = project_deep_link(
            project,
            tab="wbs",
            node=activity.wbs_node_id,
        )
        for membership in members:
            create_notification(
                membership.user,
                Notification.NotificationType.MILESTONE,
                f"Веха: {activity.wbs_node.title}",
                f"Проект «{project.name}» — {activity.start_date}",
                link,
                workspace=workspace,
            )


def check_birthday_reminders(user):
    from birthdays.models import Contact

    memberships = WorkspaceMember.objects.filter(user=user).select_related("workspace")
    today = date.today()
    for membership in memberships:
        for contact in Contact.objects.filter(
            workspace=membership.workspace
        ).select_related("birthday"):
            days = days_until_birthday(contact.birthday.birth_date, today)
            if days > 7:
                continue
            exists = Notification.objects.filter(
                user=user,
                workspace=membership.workspace,
                notification_type=Notification.NotificationType.BIRTHDAY,
                title__contains=contact.name,
                created_at__date=today,
            ).exists()
            if exists:
                continue
            create_notification(
                user,
                Notification.NotificationType.BIRTHDAY,
                f"ДР: {contact.name}",
                f"Через {days} дн.",
                f"/calendar?workspace={membership.workspace_id}",
                workspace=membership.workspace,
            )
