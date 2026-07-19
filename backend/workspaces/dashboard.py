from datetime import date

from django.db.models import Sum
from django.utils import timezone

from finance.models import Transaction
from notifications.models import Notification
from projects.cpm import compute_evm_lite
from projects.models import Project, Risk, ScheduleActivity


def build_workspace_dashboard(workspace, user, *, limit_overdue=10, limit_risks=5):
    today = date.today()
    projects = list(
        Project.objects.filter(workspace=workspace)
        .exclude(status__in=[Project.Status.COMPLETED, Project.Status.CANCELLED])
        .order_by("name", "id")
    )
    project_ids = [project.id for project in projects]

    overdue_qs = (
        ScheduleActivity.objects.filter(
            wbs_node__project_id__in=project_ids,
            end_date__lt=today,
            progress__lt=100,
        )
        .select_related(
            "wbs_node",
            "wbs_node__project",
            "wbs_node__assignee",
            "wbs_node__workflow_status",
        )
        .order_by("end_date", "id")
    )
    overdue_items = []
    for activity in overdue_qs[:limit_overdue]:
        node = activity.wbs_node
        project = node.project
        overdue_items.append(
            {
                "activity_id": activity.id,
                "wbs_id": node.id,
                "wbs_code": node.code,
                "title": node.title,
                "project_id": project.id,
                "project_name": project.name,
                "end_date": activity.end_date.isoformat(),
                "progress": activity.progress,
                "assignee_id": node.assignee_id,
                "assignee_name": (
                    node.assignee.get_full_name() or node.assignee.email
                    if node.assignee
                    else None
                ),
                "days_overdue": (today - activity.end_date).days,
            }
        )

    open_risks = (
        Risk.objects.filter(
            project_id__in=project_ids,
            status=Risk.Status.OPEN,
        )
        .select_related("project")
        .order_by("-probability", "-impact", "id")
    )
    top_risks = [
        {
            "id": risk.id,
            "title": risk.title,
            "score": risk.score,
            "probability": risk.probability,
            "impact": risk.impact,
            "status": risk.status,
            "project_id": risk.project_id,
            "project_name": risk.project.name,
        }
        for risk in open_risks[:limit_risks]
    ]

    expense_map = {
        row["project_id"]: float(row["total"] or 0)
        for row in Transaction.objects.filter(
            project_id__in=project_ids,
            transaction_type=Transaction.TransactionType.EXPENSE,
        )
        .values("project_id")
        .annotate(total=Sum("amount"))
    }

    project_health = []
    for project in projects:
        activities = list(
            ScheduleActivity.objects.filter(wbs_node__project=project).select_related(
                "wbs_node"
            )
        )
        overdue_count = sum(
            1
            for activity in activities
            if activity.end_date
            and activity.end_date < today
            and activity.progress < 100
        )
        progress = (
            round(sum(activity.progress for activity in activities) / len(activities))
            if activities
            else 0
        )
        evm = compute_evm_lite(
            project,
            activities,
            actual_cost=expense_map.get(project.id, 0),
        )
        project_health.append(
            {
                "project_id": project.id,
                "name": project.name,
                "status": project.status,
                "progress": progress,
                "budget": float(project.budget or 0),
                "spi": evm["spi"],
                "cpi": evm["cpi"],
                "overdue_count": overdue_count,
            }
        )

    unread_qs = Notification.objects.filter(
        user=user,
        workspace=workspace,
        is_read=False,
    ).order_by("-created_at")
    unread_notifications = [
        {
            "id": item.id,
            "notification_type": item.notification_type,
            "title": item.title,
            "message": item.message,
            "link": item.link,
            "created_at": item.created_at.isoformat(),
        }
        for item in unread_qs[:5]
    ]

    return {
        "workspace_id": workspace.id,
        "generated_at": timezone.now().isoformat(),
        "summary": {
            "project_count": len(projects),
            "overdue_count": overdue_qs.count(),
            "open_risk_count": open_risks.count(),
            "unread_notification_count": unread_qs.count(),
        },
        "overdue_tasks": overdue_items,
        "top_risks": top_risks,
        "project_health": project_health,
        "unread_notifications": unread_notifications,
    }
