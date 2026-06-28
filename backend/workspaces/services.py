from workspaces.models import Workspace


def get_user_workspace(user):
    return (
        Workspace.objects.filter(memberships__user=user)
        .order_by("created_at")
        .first()
    )
