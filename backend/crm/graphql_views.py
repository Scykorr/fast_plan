"""Lightweight read-only GraphQL-style API for CRM (no graphene dependency)."""

from __future__ import annotations

import re

from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from crm.models import Deal, Lead, Organization, Person
from workspaces.mixins import IsWorkspaceEditorOrReadOnly, WorkspaceMixin


def _pick_fields(obj: dict, wanted: list[str] | None) -> dict:
    if not wanted:
        return obj
    return {k: obj[k] for k in wanted if k in obj}


def _parse_selection(query: str, root: str) -> list[str]:
    """
    Very small parser: organizations { id name } → ['id','name']
    Ignores nested selections.
    """
    pattern = rf"{root}\s*\{{([^}}]*)\}}"
    match = re.search(pattern, query, re.IGNORECASE | re.DOTALL)
    if not match:
        return []
    body = match.group(1)
    return [tok for tok in re.split(r"[\s,]+", body.strip()) if tok and not tok.startswith("#")]


class CrmGraphqlView(WorkspaceMixin, APIView):
    """
    POST /api/crm/graphql/
    Body: { "query": "{ organizations { id name } deals { id title amount } }" }
    """

    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def post(self, request):
        query = (request.data.get("query") or "").strip()
        if not query:
            raise ValidationError({"query": "Required"})
        ws = self.get_workspace()
        data: dict = {}

        if re.search(r"\borganizations\b", query, re.I):
            fields = _parse_selection(query, "organizations") or [
                "id",
                "name",
                "website",
                "industry",
            ]
            rows = []
            for o in Organization.objects.filter(workspace=ws)[:100]:
                rows.append(
                    _pick_fields(
                        {
                            "id": o.id,
                            "name": o.name,
                            "website": o.website,
                            "industry": o.industry,
                        },
                        fields,
                    )
                )
            data["organizations"] = rows

        if re.search(r"\bpeople\b", query, re.I):
            fields = _parse_selection(query, "people") or [
                "id",
                "full_name",
                "email",
                "phone",
            ]
            rows = []
            for p in Person.objects.filter(workspace=ws)[:100]:
                rows.append(
                    _pick_fields(
                        {
                            "id": p.id,
                            "full_name": p.full_name,
                            "email": p.email,
                            "phone": p.phone,
                        },
                        fields,
                    )
                )
            data["people"] = rows

        if re.search(r"\bdeals\b", query, re.I):
            fields = _parse_selection(query, "deals") or [
                "id",
                "title",
                "amount",
                "probability",
            ]
            rows = []
            for d in Deal.objects.filter(workspace=ws).select_related("stage")[:100]:
                rows.append(
                    _pick_fields(
                        {
                            "id": d.id,
                            "title": d.title,
                            "amount": float(d.amount or 0),
                            "probability": d.probability,
                            "stage": d.stage.name if d.stage_id else None,
                        },
                        fields,
                    )
                )
            data["deals"] = rows

        if re.search(r"\bleads\b", query, re.I):
            fields = _parse_selection(query, "leads") or ["id", "full_name", "status", "score"]
            rows = []
            for lead in Lead.objects.filter(workspace=ws)[:100]:
                rows.append(
                    _pick_fields(
                        {
                            "id": lead.id,
                            "full_name": lead.full_name,
                            "name": lead.full_name,
                            "status": lead.status,
                            "score": lead.score,
                            "source": lead.source,
                        },
                        fields,
                    )
                )
            data["leads"] = rows

        if not data:
            raise ValidationError(
                {
                    "query": "Supported roots: organizations, people, deals, leads. "
                    "Example: { organizations { id name } }"
                }
            )
        return Response({"data": data})
