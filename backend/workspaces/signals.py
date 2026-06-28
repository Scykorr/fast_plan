from django.db.models.signals import post_save
from django.dispatch import receiver

from accounts.models import User
from workspaces.models import Workspace, WorkspaceMember


@receiver(post_save, sender=User)
def create_default_workspace(sender, instance, created, **kwargs):
    if not created:
        return
    workspace = Workspace.objects.create(
        name="Моё пространство",
        owner=instance,
    )
    WorkspaceMember.objects.create(
        workspace=workspace,
        user=instance,
        role=WorkspaceMember.Role.OWNER,
    )
