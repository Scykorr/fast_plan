"""AI CRM API endpoints."""

from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from crm import ai as crm_ai
from workspaces.mixins import IsWorkspaceEditorOrReadOnly, WorkspaceMixin


def _optional_int(data, key):
    raw = data.get(key)
    if raw in (None, ""):
        return None
    try:
        return int(raw)
    except (TypeError, ValueError) as exc:
        raise ValidationError({key: "Must be an integer."}) from exc


class CrmAiInsightsView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get(self, request):
        stale_days = 14
        raw = request.query_params.get("stale_days")
        if raw not in (None, ""):
            try:
                stale_days = max(1, int(raw))
            except (TypeError, ValueError) as exc:
                raise ValidationError({"stale_days": "Must be an integer."}) from exc
        return Response(crm_ai.build_crm_insights(self.get_workspace(), stale_days=stale_days))


class CrmAiDraftEmailView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def post(self, request):
        return Response(
            crm_ai.draft_email(
                self.get_workspace(),
                deal_id=_optional_int(request.data, "deal_id"),
                person_id=_optional_int(request.data, "person_id"),
                organization_id=_optional_int(request.data, "organization_id"),
                prompt=str(request.data.get("prompt") or ""),
            )
        )


class CrmAiDraftKpView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def post(self, request):
        return Response(
            crm_ai.draft_kp(
                self.get_workspace(),
                deal_id=_optional_int(request.data, "deal_id"),
                person_id=_optional_int(request.data, "person_id"),
                organization_id=_optional_int(request.data, "organization_id"),
                prompt=str(request.data.get("prompt") or ""),
            )
        )


class CrmAiActivitySummaryView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def post(self, request):
        return Response(
            crm_ai.summarize_activity(
                self.get_workspace(),
                deal_id=_optional_int(request.data, "deal_id"),
                person_id=_optional_int(request.data, "person_id"),
                organization_id=_optional_int(request.data, "organization_id"),
                prompt=str(request.data.get("prompt") or ""),
            )
        )


class CrmAiSuggestTasksView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def post(self, request):
        deal_id = _optional_int(request.data, "deal_id")
        if not deal_id:
            raise ValidationError({"deal_id": "Required."})
        apply = bool(request.data.get("apply"))
        result = crm_ai.suggest_deal_tasks(
            self.get_workspace(), deal_id=deal_id, apply=apply
        )
        if result.get("error"):
            raise ValidationError({"deal_id": result["error"]})
        return Response(result)
