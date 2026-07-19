from django.db.models.signals import post_save
from django.dispatch import receiver

from notifications.models import Notification
from notifications.services import create_notification, project_deep_link, send_milestone_reminders
from projects.models import Project, Risk
from workspaces.models import WorkspaceMember


@receiver(post_save, sender=Risk)
def notify_high_risk(sender, instance, created, **kwargs):
    if not created or instance.score < 15:
        return
    project = instance.project
    members = WorkspaceMember.objects.filter(workspace=project.workspace).select_related(
        "user"
    )
    link = project_deep_link(project, tab="risks", risk=instance.id)
    dedupe = f"risk:{instance.id}"
    for membership in members:
        create_notification(
            user=membership.user,
            notification_type=Notification.NotificationType.RISK,
            title=f"Высокий риск: {instance.title}",
            message=f"Проект «{project.name}» — оценка {instance.score}",
            link=link,
            workspace=project.workspace,
            dedupe_key=dedupe,
        )


@receiver(post_save, sender=Project)
def notify_upcoming_milestones_on_create(sender, instance, created, **kwargs):
    if not created:
        return
    send_milestone_reminders()
