from django.db.models.signals import post_save
from django.dispatch import receiver

from projects.models import Project, ProjectCharter
from projects.services import (
    _default_project_tracker,
    _default_workflow_status,
    create_project_board,
    create_root_wbs_node,
)


@receiver(post_save, sender=Project)
def setup_project_defaults(sender, instance, created, **kwargs):
    if not created:
        return
    from tracking.services import seed_workspace_tracking

    seed_workspace_tracking(instance.workspace)
    instance.tracker = _default_project_tracker(instance.workspace)
    instance.workflow_status = _default_workflow_status(instance.workspace)
    instance.save(update_fields=["tracker", "workflow_status"])
    create_project_board(instance)
    create_root_wbs_node(instance)
    ProjectCharter.objects.get_or_create(project=instance)
