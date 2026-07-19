import secrets
from datetime import timedelta

from django.utils import timezone

from workspaces.models import WorkspaceInvitation, WorkspaceMember


def create_workspace_invitation(workspace, email, role, invited_by):
    return WorkspaceInvitation.objects.create(
        workspace=workspace,
        email=email.lower().strip(),
        role=role,
        token=secrets.token_urlsafe(32),
        invited_by=invited_by,
        expires_at=timezone.now() + timedelta(days=7),
    )


def accept_invitation(token, user):
    invitation = WorkspaceInvitation.objects.select_related("workspace").get(token=token)
    if invitation.is_accepted:
        raise ValueError("Invitation already accepted.")
    if invitation.is_expired:
        raise ValueError("Invitation expired.")
    if user.email.lower() != invitation.email.lower():
        raise ValueError("Invitation email does not match.")

    WorkspaceMember.objects.get_or_create(
        workspace=invitation.workspace,
        user=user,
        defaults={"role": invitation.role},
    )
    invitation.accepted_at = timezone.now()
    invitation.save(update_fields=["accepted_at"])

    from workspaces.services import set_active_workspace

    set_active_workspace(user, invitation.workspace)
    return invitation.workspace
