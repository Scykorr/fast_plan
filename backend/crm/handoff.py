"""Deal → Project handoff (P10 sprint 1)."""

from __future__ import annotations

from django.db import transaction
from rest_framework.exceptions import ValidationError

from crm.models import Deal
from projects.models import Project, ProjectTemplate
from projects.serializers import ProjectListSerializer
from projects.templates import apply_project_template


@transaction.atomic
def create_project_from_deal(
    deal: Deal,
    *,
    user,
    template_id: int | None = None,
    require_won: bool = False,
) -> tuple[Deal, Project]:
    if deal.project_id:
        raise ValidationError(
            {"project": "Deal already linked to a project."}
        )
    if require_won and not (deal.stage and deal.stage.is_won):
        raise ValidationError(
            {"stage": "Deal must be in a won stage (or pass require_won=false)."}
        )

    name = (deal.title or "").strip() or f"Deal #{deal.id}"
    project = Project.objects.create(
        workspace=deal.workspace,
        name=name[:255],
        description=(deal.notes or "")[:2000],
        manager=user if getattr(user, "is_authenticated", False) else None,
        client_organization=deal.organization,
        status=Project.Status.PLANNING,
    )

    if template_id:
        template = ProjectTemplate.objects.filter(
            pk=template_id, workspace=deal.workspace
        ).first()
        if template is None:
            raise ValidationError({"template_id": "Template not found."})
        apply_project_template(project, template)

    deal.project = project
    deal.save(update_fields=["project", "updated_at"])
    return deal, project


def serialize_handoff(deal: Deal, project: Project) -> dict:
    from crm.serializers import DealSerializer

    return {
        "deal": DealSerializer(deal).data,
        "project": ProjectListSerializer(project).data,
    }
