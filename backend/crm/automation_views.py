from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from crm.automation import AUTOMATION_TEMPLATES, apply_template, run_automations
from crm.models import AutomationRule, AutomationRun
from crm.serializers import (
    AutomationRuleSerializer,
    AutomationRuleWriteSerializer,
    AutomationRunSerializer,
)
from workspaces.mixins import IsWorkspaceEditorOrReadOnly, WorkspaceMixin


class AutomationListCreateView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get(self, request):
        rules = AutomationRule.objects.filter(workspace=self.get_workspace())
        return Response(AutomationRuleSerializer(rules, many=True).data)

    def post(self, request):
        serializer = AutomationRuleWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if not data.get("name") or not data.get("trigger"):
            raise ValidationError({"detail": "name and trigger are required."})
        rule = AutomationRule.objects.create(
            workspace=self.get_workspace(),
            name=data["name"],
            trigger=data["trigger"],
            conditions=data.get("conditions") or [],
            actions=data.get("actions") or [],
            is_active=data.get("is_active", True),
            template_key=data.get("template_key") or "",
        )
        return Response(
            AutomationRuleSerializer(rule).data, status=status.HTTP_201_CREATED
        )


class AutomationDetailView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get_object(self, rule_id):
        return get_object_or_404(
            AutomationRule.objects.filter(workspace=self.get_workspace()),
            pk=rule_id,
        )

    def get(self, request, rule_id):
        return Response(AutomationRuleSerializer(self.get_object(rule_id)).data)

    def patch(self, request, rule_id):
        rule = self.get_object(rule_id)
        serializer = AutomationRuleWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        for field in ("name", "trigger", "conditions", "actions", "is_active", "template_key"):
            if field in data:
                setattr(rule, field, data[field])
        rule.save()
        return Response(AutomationRuleSerializer(rule).data)

    def delete(self, request, rule_id):
        self.get_object(rule_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AutomationTemplateListView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get(self, request):
        items = [
            {
                "key": key,
                "name": value["name"],
                "trigger": value["trigger"],
                "conditions": value["conditions"],
                "actions": value["actions"],
            }
            for key, value in AUTOMATION_TEMPLATES.items()
        ]
        return Response(items)


class AutomationTemplateApplyView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def post(self, request):
        key = request.data.get("template_key") or request.data.get("key")
        if not key:
            raise ValidationError({"template_key": "Required."})
        try:
            rule = apply_template(self.get_workspace(), key)
        except ValueError as exc:
            raise ValidationError({"template_key": str(exc)})
        return Response(
            AutomationRuleSerializer(rule).data, status=status.HTTP_201_CREATED
        )


class AutomationRunListView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get(self, request):
        runs = (
            AutomationRun.objects.filter(workspace=self.get_workspace())
            .select_related("rule")[:100]
        )
        return Response(AutomationRunSerializer(runs, many=True).data)


class AutomationTestView(WorkspaceMixin, APIView):
    """Dry-fire a trigger against current workspace (optional lead_id/deal_id)."""

    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def post(self, request):
        from crm.automation import build_deal_context, build_lead_context
        from crm.models import Deal, Lead

        trigger = request.data.get("trigger")
        if trigger not in AutomationRule.Trigger.values:
            raise ValidationError({"trigger": "Invalid trigger."})
        workspace = self.get_workspace()
        context = {"trigger": trigger}
        lead_id = request.data.get("lead_id")
        deal_id = request.data.get("deal_id")
        if lead_id:
            lead = get_object_or_404(Lead.objects.filter(workspace=workspace), pk=lead_id)
            context.update(build_lead_context(lead, trigger=trigger))
        if deal_id:
            deal = get_object_or_404(Deal.objects.filter(workspace=workspace), pk=deal_id)
            context.update(build_deal_context(deal, trigger=trigger))
        runs = run_automations(workspace, trigger, context)
        return Response(
            {
                "ran": len(runs),
                "runs": AutomationRunSerializer(runs, many=True).data,
            }
        )
