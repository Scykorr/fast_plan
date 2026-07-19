from django.db.models import Sum
from django.utils import timezone

from projects.cpm import compute_critical_path, compute_evm_lite
from projects.models import ProjectCharter, ScheduleActivity
from projects.serializers import ScheduleActivitySerializer
from projects.serializers_pmbok import (
    ProjectCharterSerializer,
    RiskSerializer,
    StakeholderSerializer,
)


def build_status_report(project) -> dict:
    activities = list(
        ScheduleActivity.objects.filter(wbs_node__project=project).select_related(
            "wbs_node"
        )
    )
    charter = getattr(project, "charter", None)
    if charter is None:
        charter, _ = ProjectCharter.objects.get_or_create(project=project)

    from finance.models import Transaction

    actual_cost = float(
        Transaction.objects.filter(
            project=project,
            transaction_type=Transaction.TransactionType.EXPENSE,
        ).aggregate(total=Sum("amount"))["total"]
        or 0
    )
    progress = (
        round(sum(a.progress for a in activities) / len(activities))
        if activities
        else 0
    )
    return {
        "project": {
            "id": project.id,
            "name": project.name,
            "status": project.status,
            "budget": float(project.budget or 0),
            "start_date": project.start_date,
            "end_date": project.end_date,
            "description": project.description,
        },
        "charter": ProjectCharterSerializer(charter).data,
        "progress": progress,
        "evm": compute_evm_lite(project, activities, actual_cost),
        "critical_path": compute_critical_path(project),
        "top_risks": RiskSerializer(project.risks.all()[:5], many=True).data,
        "stakeholders": StakeholderSerializer(
            project.stakeholders.all(), many=True
        ).data,
        "milestones": ScheduleActivitySerializer(
            [a for a in activities if a.is_milestone],
            many=True,
        ).data,
        "generated_at": timezone.now().isoformat(),
    }
