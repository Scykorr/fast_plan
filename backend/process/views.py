"""Process API views (BPMN / DMN / CMMN / packs / metrics)."""

from __future__ import annotations

from pathlib import Path

from django.utils import timezone
from django.utils.text import slugify
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from process.engine import complete_user_task, parse_process_id, start_instance
from process.metrics import build_process_metrics
from process.migration_tools import automation_rule_to_bpmn
from process.models import (
    CaseDefinition,
    CaseInstance,
    DecisionDefinition,
    ProcessDefinition,
    ProcessInstance,
    UserTask,
)
from process.serializers import (
    CaseDefinitionSerializer,
    CaseInstanceSerializer,
    DecisionDefinitionSerializer,
    ProcessDefinitionSerializer,
    ProcessInstanceSerializer,
    UserTaskSerializer,
)
from process.services import publish_definition
from workspaces.mixins import IsWorkspaceEditorOrReadOnly, WorkspaceMixin

PACKS_DIR = Path(__file__).resolve().parent / "packs"


class ProcessDefinitionListCreateView(WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def get(self, request):
        qs = ProcessDefinition.objects.filter(workspace=self.get_workspace())
        return Response(ProcessDefinitionSerializer(qs, many=True).data)

    def post(self, request):
        workspace = self.get_workspace()
        ser = ProcessDefinitionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        bpmn_xml = ser.validated_data["bpmn_xml"]
        process_id = ser.validated_data.get("process_id") or parse_process_id(bpmn_xml)
        obj = ProcessDefinition.objects.create(
            workspace=workspace,
            key=ser.validated_data["key"],
            name=ser.validated_data["name"],
            description=ser.validated_data.get("description") or "",
            bpmn_xml=bpmn_xml,
            process_id=process_id,
            category=ser.validated_data.get("category") or "",
            created_by=request.user,
        )
        return Response(
            ProcessDefinitionSerializer(obj).data, status=status.HTTP_201_CREATED
        )


class ProcessDefinitionDetailView(WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def _get(self, pk):
        obj = ProcessDefinition.objects.filter(
            workspace=self.get_workspace(), pk=pk
        ).first()
        if obj is None:
            raise NotFound()
        return obj

    def get(self, request, pk):
        return Response(ProcessDefinitionSerializer(self._get(pk)).data)

    def patch(self, request, pk):
        obj = self._get(pk)
        for field in ("name", "description", "bpmn_xml", "category", "key"):
            if field in request.data:
                setattr(obj, field, request.data[field])
        if "bpmn_xml" in request.data:
            obj.process_id = parse_process_id(obj.bpmn_xml)
            obj.version += 1
            obj.is_published = False
        obj.save()
        return Response(ProcessDefinitionSerializer(obj).data)

    def delete(self, request, pk):
        self._get(pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProcessPublishView(WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def post(self, request, pk):
        obj = ProcessDefinition.objects.filter(
            workspace=self.get_workspace(), pk=pk
        ).first()
        if obj is None:
            raise NotFound()
        deployment = publish_definition(obj, user=request.user)
        return Response(
            {
                "definition": ProcessDefinitionSerializer(obj).data,
                "deployment_id": deployment.id,
            }
        )


class ProcessStartView(WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def post(self, request, pk):
        definition = ProcessDefinition.objects.filter(
            workspace=self.get_workspace(), pk=pk, is_published=True
        ).first()
        if definition is None:
            raise NotFound("Published definition not found")
        deployment = publish_definition(definition, user=request.user)
        instance = ProcessInstance.objects.create(
            workspace=self.get_workspace(),
            deployment=deployment,
            business_key=str(request.data.get("business_key") or ""),
            deal_id=request.data.get("deal_id"),
            project_id=request.data.get("project_id"),
            organization_id=request.data.get("organization_id"),
            data=request.data.get("data") or {},
            started_by=request.user,
        )
        start_instance(instance)
        return Response(
            ProcessInstanceSerializer(instance).data, status=status.HTTP_201_CREATED
        )


class ProcessInstanceListView(WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def get(self, request):
        qs = ProcessInstance.objects.filter(workspace=self.get_workspace()).select_related(
            "deployment__definition"
        )[:100]
        return Response(ProcessInstanceSerializer(qs, many=True).data)


class ProcessInstanceDetailView(WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def get(self, request, pk):
        obj = (
            ProcessInstance.objects.filter(workspace=self.get_workspace(), pk=pk)
            .select_related("deployment__definition")
            .first()
        )
        if obj is None:
            raise NotFound()
        tasks = UserTask.objects.filter(instance=obj)
        return Response(
            {
                "instance": ProcessInstanceSerializer(obj).data,
                "user_tasks": UserTaskSerializer(tasks, many=True).data,
                "bpmn_xml": obj.deployment.bpmn_xml,
            }
        )


class UserTaskListView(WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def get(self, request):
        qs = UserTask.objects.filter(workspace=self.get_workspace()).select_related(
            "instance__deployment__definition"
        )
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        mine = request.query_params.get("mine")
        if mine in ("1", "true", "yes"):
            qs = qs.filter(assignee=request.user)
        return Response(UserTaskSerializer(qs[:100], many=True).data)


class UserTaskCompleteView(WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def post(self, request, pk):
        task = UserTask.objects.filter(workspace=self.get_workspace(), pk=pk).first()
        if task is None:
            raise NotFound()
        form_data = request.data.get("form_data") or {}
        # P8c: merge form fields from body directly
        for key, value in request.data.items():
            if key not in ("form_data",):
                form_data.setdefault(key, value)
        try:
            instance = complete_user_task(task, user=request.user, form_data=form_data)
        except ValueError as exc:
            raise ValidationError({"detail": str(exc)}) from exc
        return Response(
            {
                "task": UserTaskSerializer(task).data,
                "instance": ProcessInstanceSerializer(instance).data,
            }
        )


class DecisionListCreateView(WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def get(self, request):
        qs = DecisionDefinition.objects.filter(workspace=self.get_workspace())
        return Response(DecisionDefinitionSerializer(qs, many=True).data)

    def post(self, request):
        ser = DecisionDefinitionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        obj = DecisionDefinition.objects.create(
            workspace=self.get_workspace(), **ser.validated_data
        )
        return Response(
            DecisionDefinitionSerializer(obj).data, status=status.HTTP_201_CREATED
        )


class DecisionEvaluateView(WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def post(self, request, pk):
        from process.dmn import evaluate_decision

        decision = DecisionDefinition.objects.filter(
            workspace=self.get_workspace(), pk=pk
        ).first()
        if decision is None:
            raise NotFound()
        result = evaluate_decision(
            workspace=self.get_workspace(),
            decision_key=decision.key,
            inputs=request.data.get("inputs") or {},
        )
        return Response({"result": result})


class CaseDefinitionListCreateView(WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def get(self, request):
        qs = CaseDefinition.objects.filter(workspace=self.get_workspace())
        return Response(CaseDefinitionSerializer(qs, many=True).data)

    def post(self, request):
        ser = CaseDefinitionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        obj = CaseDefinition.objects.create(
            workspace=self.get_workspace(), **ser.validated_data
        )
        return Response(
            CaseDefinitionSerializer(obj).data, status=status.HTTP_201_CREATED
        )


class CaseInstanceListCreateView(WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def get(self, request):
        qs = CaseInstance.objects.filter(workspace=self.get_workspace()).select_related(
            "definition"
        )[:100]
        return Response(CaseInstanceSerializer(qs, many=True).data)

    def post(self, request):
        definition = CaseDefinition.objects.filter(
            workspace=self.get_workspace(), pk=request.data.get("definition_id")
        ).first()
        if definition is None:
            raise ValidationError({"definition_id": "Required"})
        obj = CaseInstance.objects.create(
            workspace=self.get_workspace(),
            definition=definition,
            title=request.data.get("title") or definition.name,
            deal_id=request.data.get("deal_id"),
            project_id=request.data.get("project_id"),
            data=request.data.get("data") or {},
            started_by=request.user,
        )
        return Response(
            CaseInstanceSerializer(obj).data, status=status.HTTP_201_CREATED
        )


class CaseInstanceCompleteItemView(WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def post(self, request, pk):
        case = CaseInstance.objects.filter(
            workspace=self.get_workspace(), pk=pk
        ).first()
        if case is None:
            raise NotFound()
        item_id = str(request.data.get("item_id") or "")
        if not item_id:
            raise ValidationError({"item_id": "Required"})
        completed = list(case.completed_items or [])
        if item_id not in completed:
            completed.append(item_id)
        case.completed_items = completed
        # Optional: start linked process
        process_key = request.data.get("process_key")
        if process_key:
            definition = ProcessDefinition.objects.filter(
                workspace=self.get_workspace(),
                key=process_key,
                is_published=True,
            ).first()
            if definition:
                from process.services import publish_definition

                deployment = publish_definition(definition, user=request.user)
                instance = ProcessInstance.objects.create(
                    workspace=self.get_workspace(),
                    deployment=deployment,
                    deal_id=case.deal_id,
                    project_id=case.project_id,
                    data={"case_id": case.id, "item_id": item_id},
                    started_by=request.user,
                )
                start_instance(instance)
        case.save(update_fields=["completed_items"])
        return Response(CaseInstanceSerializer(case).data)


class CaseInstanceCloseView(WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def post(self, request, pk):
        case = CaseInstance.objects.filter(
            workspace=self.get_workspace(), pk=pk
        ).first()
        if case is None:
            raise NotFound()
        case.status = CaseInstance.Status.CLOSED
        case.closed_at = timezone.now()
        case.save(update_fields=["status", "closed_at"])
        return Response(CaseInstanceSerializer(case).data)


class ProcessPackListView(WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def get(self, request):
        packs = []
        if PACKS_DIR.exists():
            for path in sorted(PACKS_DIR.glob("*.bpmn")):
                meta = path.with_suffix(".md")
                packs.append(
                    {
                        "id": path.stem,
                        "name": path.stem.replace("_", " ").title(),
                        "filename": path.name,
                        "readme": meta.read_text(encoding="utf-8")
                        if meta.exists()
                        else "",
                    }
                )
        return Response(packs)


class ProcessPackImportView(WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def post(self, request):
        pack_id = request.data.get("pack_id")
        if not pack_id:
            raise ValidationError({"pack_id": "Required"})
        path = PACKS_DIR / f"{pack_id}.bpmn"
        if not path.exists():
            raise NotFound("Pack not found")
        xml = path.read_text(encoding="utf-8")
        process_id = parse_process_id(xml)
        key = slugify(pack_id)[:80]
        obj, created = ProcessDefinition.objects.update_or_create(
            workspace=self.get_workspace(),
            key=key,
            version=1,
            defaults={
                "name": pack_id.replace("_", " ").title(),
                "description": f"Imported pack {pack_id}",
                "bpmn_xml": xml,
                "process_id": process_id,
                "category": "pack",
                "created_by": request.user,
            },
        )
        # Also import companion DMN if present
        dmn_path = PACKS_DIR / f"{pack_id}.dmn"
        if dmn_path.exists():
            dmn_xml = dmn_path.read_text(encoding="utf-8")
            DecisionDefinition.objects.update_or_create(
                workspace=self.get_workspace(),
                key=f"{key}-decision",
                version=1,
                defaults={
                    "name": f"{pack_id} decision",
                    "dmn_xml": dmn_xml,
                    "decision_id": "decision_1",
                },
            )
        return Response(
            {
                "created": created,
                "definition": ProcessDefinitionSerializer(obj).data,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class ProcessExportView(WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def get(self, request, pk):
        obj = ProcessDefinition.objects.filter(
            workspace=self.get_workspace(), pk=pk
        ).first()
        if obj is None:
            raise NotFound()
        return Response(
            {
                "key": obj.key,
                "name": obj.name,
                "process_id": obj.process_id,
                "bpmn_xml": obj.bpmn_xml,
                "version": obj.version,
            }
        )


class ProcessMigrateAutomationView(WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def post(self, request):
        from crm.models import AutomationRule

        rule_id = request.data.get("automation_rule_id")
        rule = AutomationRule.objects.filter(
            workspace=self.get_workspace(), pk=rule_id
        ).first()
        if rule is None:
            raise NotFound("Automation rule not found")
        payload = automation_rule_to_bpmn(rule)
        obj = ProcessDefinition.objects.create(
            workspace=self.get_workspace(),
            key=payload["key"],
            name=payload["name"],
            description=payload["description"],
            bpmn_xml=payload["bpmn_xml"],
            process_id=payload["process_id"],
            category=payload["category"],
            created_by=request.user,
        )
        return Response(
            ProcessDefinitionSerializer(obj).data, status=status.HTTP_201_CREATED
        )


class ProcessMetricsView(WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def get(self, request):
        return Response(build_process_metrics(self.get_workspace()))
