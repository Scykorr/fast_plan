"""Quote (CrmDocument) → WBS work packages."""

from __future__ import annotations

from django.db import transaction
from rest_framework.exceptions import ValidationError

from crm.handoff import create_project_from_deal
from crm.models import CrmDocument
from projects.models import WBSNode
from projects.services import create_work_package


@transaction.atomic
def create_wbs_from_quote(document: CrmDocument, *, user) -> dict:
    if document.doc_type != CrmDocument.DocType.QUOTE:
        raise ValidationError({"doc_type": "Only quotes can create WBS."})
    if not document.deal_id:
        raise ValidationError({"deal": "Quote must be linked to a deal."})

    deal = document.deal
    project = document.project or deal.project
    created_project = False
    if project is None:
        deal, project = create_project_from_deal(
            deal, user=user, require_won=False
        )
        created_project = True

    root = (
        project.wbs_nodes.filter(parent__isnull=True)
        .order_by("position", "id")
        .first()
    )
    if root is None:
        raise ValidationError({"project": "Project has no root WBS node."})

    created_nodes: list[WBSNode] = []
    for item in document.line_items or []:
        if not isinstance(item, dict):
            continue
        title = (
            str(item.get("title") or item.get("name") or item.get("sku_title") or "")
            .strip()
        )
        if not title:
            continue
        node = create_work_package(project, root, title[:255])
        created_nodes.append(node)

    if document.project_id != project.id:
        document.project = project
        document.save(update_fields=["project", "updated_at"])

    return {
        "document_id": document.id,
        "deal_id": deal.id,
        "project_id": project.id,
        "created_project": created_project,
        "created_wbs_ids": [n.id for n in created_nodes],
        "created_count": len(created_nodes),
    }
