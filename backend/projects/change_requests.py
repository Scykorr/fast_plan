"""Project change requests linked to baselines (P10 sprint 4)."""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from projects.baseline import create_baseline
from projects.models import ProjectChangeRequest


@transaction.atomic
def create_change_request(project, *, title: str, user, **fields) -> ProjectChangeRequest:
    title = (title or "").strip()
    if not title:
        raise ValidationError({"title": "Required."})
    change_type = fields.get("change_type") or ProjectChangeRequest.ChangeType.OTHER
    if change_type not in ProjectChangeRequest.ChangeType.values:
        raise ValidationError({"change_type": "Invalid change type."})
    status = fields.get("status") or ProjectChangeRequest.Status.SUBMITTED
    if status not in (
        ProjectChangeRequest.Status.DRAFT,
        ProjectChangeRequest.Status.SUBMITTED,
    ):
        raise ValidationError({"status": "New CRs must be draft or submitted."})
    return ProjectChangeRequest.objects.create(
        project=project,
        title=title,
        description=str(fields.get("description") or ""),
        change_type=change_type,
        status=status,
        impact_notes=str(fields.get("impact_notes") or ""),
        requested_by=user,
    )


@transaction.atomic
def decide_change_request(
    cr: ProjectChangeRequest,
    *,
    action: str,
    user,
    note: str = "",
    create_baseline_on_approve: bool = True,
) -> ProjectChangeRequest:
    action = (action or "").strip().lower()
    if cr.status not in (
        ProjectChangeRequest.Status.DRAFT,
        ProjectChangeRequest.Status.SUBMITTED,
    ):
        raise ValidationError({"detail": f"Cannot decide CR in status '{cr.status}'."})
    if action == "approve":
        cr.status = ProjectChangeRequest.Status.APPROVED
        if create_baseline_on_approve and cr.baseline_id is None:
            baseline = create_baseline(
                cr.project,
                f"CR-{cr.id}: {cr.title}"[:255],
                user,
            )
            cr.baseline = baseline
    elif action == "reject":
        cr.status = ProjectChangeRequest.Status.REJECTED
    else:
        raise ValidationError({"action": "Must be 'approve' or 'reject'."})
    cr.decision_note = str(note or "")
    cr.decided_by = user
    cr.decided_at = timezone.now()
    cr.save(
        update_fields=[
            "status",
            "decision_note",
            "decided_by",
            "decided_at",
            "baseline",
            "updated_at",
        ]
    )
    return cr
