from django.db.models.signals import post_save
from django.dispatch import receiver

from projects.models import Project
from projects.services import create_project_board, create_root_wbs_node


@receiver(post_save, sender=Project)
def setup_project_defaults(sender, instance, created, **kwargs):
    if not created:
        return
    create_project_board(instance)
    create_root_wbs_node(instance)
