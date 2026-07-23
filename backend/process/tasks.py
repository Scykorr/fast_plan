from celery import shared_task
from django.utils import timezone


@shared_task(name="process.fire_due_timers")
def fire_due_timers():
    from process.engine import fire_timer
    from process.models import ProcessTimer, UserTask
    from notifications.services import create_notification
    from notifications.models import Notification

    now = timezone.now()
    timers = ProcessTimer.objects.filter(fired=False, fire_at__lte=now).select_related(
        "instance"
    )[:100]
    for timer in timers:
        fire_timer(timer)

    # P8c: escalate overdue user tasks with a reminder notification
    overdue = UserTask.objects.filter(
        status=UserTask.Status.OPEN,
        due_at__lte=now,
        reminded_at__isnull=True,
    ).select_related("assignee", "workspace")[:100]
    for task in overdue:
        if task.assignee_id:
            create_notification(
                user=task.assignee,
                notification_type=Notification.NotificationType.DEADLINE,
                title=f"Просрочена задача процесса: {task.name}",
                message="Срок user task истёк",
                link=f"/process-tasks",
                workspace=task.workspace,
                dedupe_key=f"process-task-overdue:{task.id}",
            )
        task.reminded_at = now
        task.save(update_fields=["reminded_at"])
    return {"timers": len(timers), "reminders": len(overdue)}
