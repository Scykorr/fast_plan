from django.db.models.signals import post_save
from django.dispatch import receiver

from tracking.services import seed_workspace_tracking
from workspaces.models import Workspace


@receiver(post_save, sender=Workspace)
def seed_tracking_for_workspace(sender, instance, created, **kwargs):
    if created:
        seed_workspace_tracking(instance)
