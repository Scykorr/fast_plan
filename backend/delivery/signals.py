from django.db.models.signals import post_save
from django.dispatch import receiver

from delivery.defaults import get_or_create_delivery_settings
from workspaces.models import Workspace


@receiver(post_save, sender=Workspace)
def provision_delivery_settings(sender, instance, created, **kwargs):
    if created:
        get_or_create_delivery_settings(instance)
