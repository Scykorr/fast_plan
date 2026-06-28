from projects.models import BaselineActivity, ProjectBaseline, ScheduleActivity


def create_baseline(project, name: str, user) -> ProjectBaseline:
    baseline = ProjectBaseline.objects.create(
        project=project,
        name=name,
        created_by=user,
    )
    activities = ScheduleActivity.objects.filter(wbs_node__project=project)
    BaselineActivity.objects.bulk_create(
        [
            BaselineActivity(
                baseline=baseline,
                activity=activity,
                start_date=activity.start_date,
                end_date=activity.end_date,
                duration_days=activity.duration_days,
                progress=activity.progress,
            )
            for activity in activities
        ]
    )
    return baseline
