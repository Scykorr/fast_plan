import secrets
from datetime import timedelta

from django.utils import timezone

from notifications.mail import absolute_frontend_url, send_app_email
from workspaces.models import WorkspaceInvitation, WorkspaceMember


def create_workspace_invitation(workspace, email, role, invited_by):
    email = email.lower().strip()
    expires_at = timezone.now() + timedelta(days=7)
    token = secrets.token_urlsafe(32)
    invitation, _created = WorkspaceInvitation.objects.update_or_create(
        workspace=workspace,
        email=email,
        defaults={
            "role": role,
            "token": token,
            "invited_by": invited_by,
            "expires_at": expires_at,
            "accepted_at": None,
        },
    )
    send_invitation_email(invitation)
    return invitation


def send_invitation_email(invitation) -> bool:
    inviter_email = ""
    if invitation.invited_by_id:
        inviter_email = invitation.invited_by.email
    return send_app_email(
        to=invitation.email,
        subject=f"Приглашение в «{invitation.workspace.name}» — Fast Plan",
        template_base="email/invitation",
        context={
            "workspace_name": invitation.workspace.name,
            "role": invitation.role,
            "inviter_email": inviter_email,
            "expires_at": timezone.localtime(invitation.expires_at).strftime(
                "%d.%m.%Y %H:%M"
            ),
            "invite_url": absolute_frontend_url(f"/invite/{invitation.token}"),
        },
    )


def resend_workspace_invitation(invitation) -> WorkspaceInvitation:
    if invitation.is_accepted:
        raise ValueError("Invitation already accepted.")
    invitation.token = secrets.token_urlsafe(32)
    invitation.expires_at = timezone.now() + timedelta(days=7)
    invitation.save(update_fields=["token", "expires_at"])
    send_invitation_email(invitation)
    return invitation


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
