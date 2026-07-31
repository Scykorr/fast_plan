from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from crm.models import Deal, DealTask, Organization, Person, PipelineStage
from crm.serializers import (
    DealMoveSerializer,
    DealSerializer,
    DealTaskSerializer,
    DealTaskWriteSerializer,
    DealWriteSerializer,
    PipelineSerializer,
)
from crm.automation import apply_deal_move, build_deal_context, run_automations
from crm.models import AutomationRule
from crm.services import ensure_default_pipeline
from crm.task_helpers import apply_task_fields, normalize_checklist
from projects.models import Project
from workspaces.mixins import IsWorkspaceEditorOrReadOnly, WorkspaceMixin
from workspaces.models import WorkspaceMember


def _resolve_owner(workspace, owner_id):
    if owner_id is None:
        return None
    member = WorkspaceMember.objects.filter(
        workspace=workspace, user_id=owner_id
    ).first()
    if member is None:
        raise ValidationError({"owner_id": "User is not a workspace member."})
    return member.user


def _deal_queryset(workspace):
    return (
        Deal.objects.filter(workspace=workspace)
        .select_related(
            "stage",
            "organization",
            "person",
            "project",
            "owner",
            "pipeline",
        )
        .annotate(
            open_tasks_count=Count("tasks", filter=Q(tasks__is_done=False), distinct=True)
        )
    )


class PipelineBoardView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get(self, request):
        pipeline = ensure_default_pipeline(self.get_workspace())
        pipeline = (
            type(pipeline)
            .objects.prefetch_related("stages")
            .get(pk=pipeline.pk)
        )
        return Response(PipelineSerializer(pipeline).data)


class DealListCreateView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get(self, request):
        workspace = self.get_workspace()
        ensure_default_pipeline(workspace)
        qs = _deal_queryset(workspace)
        stage_id = request.query_params.get("stage_id")
        organization_id = request.query_params.get("organization_id")
        project_id = request.query_params.get("project_id")
        open_only = request.query_params.get("open")
        if stage_id:
            qs = qs.filter(stage_id=stage_id)
        if organization_id:
            qs = qs.filter(organization_id=organization_id)
        if project_id:
            qs = qs.filter(project_id=project_id)
        if open_only in ("1", "true", "True"):
            qs = qs.filter(stage__is_won=False, stage__is_lost=False)
        return Response(DealSerializer(qs[:300], many=True).data)

    def post(self, request):
        workspace = self.get_workspace()
        pipeline = ensure_default_pipeline(workspace)
        serializer = DealWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if not data.get("title"):
            raise ValidationError({"title": "This field is required."})

        stage = None
        if data.get("stage_id"):
            stage = get_object_or_404(
                PipelineStage.objects.filter(pipeline=pipeline),
                pk=data["stage_id"],
            )
        else:
            stage = pipeline.stages.order_by("position", "id").first()
            if stage is None:
                raise ValidationError("Pipeline has no stages.")

        organization = None
        if data.get("organization_id"):
            organization = get_object_or_404(
                Organization.objects.filter(workspace=workspace),
                pk=data["organization_id"],
            )
        person = None
        if data.get("person_id"):
            person = get_object_or_404(
                Person.objects.filter(workspace=workspace),
                pk=data["person_id"],
            )
        project = None
        if data.get("project_id"):
            project = get_object_or_404(
                Project.objects.filter(workspace=workspace),
                pk=data["project_id"],
            )
        owner = None
        if "owner_id" in data:
            owner = _resolve_owner(workspace, data.get("owner_id"))
        elif request.user.is_authenticated:
            owner = request.user

        probability = data.get("probability")
        if probability is None:
            probability = stage.default_probability

        deal = Deal.objects.create(
            workspace=workspace,
            pipeline=pipeline,
            stage=stage,
            title=data["title"],
            amount=data.get("amount", Decimal("0")),
            probability=probability,
            close_date=data.get("close_date"),
            organization=organization,
            person=person,
            project=project,
            owner=owner,
            position=data.get("position", 0),
            notes=data.get("notes", ""),
        )
        if "position" not in data:
            apply_deal_move(deal, stage, position=Deal.objects.filter(stage=stage).count() - 1)
        run_automations(
            workspace,
            AutomationRule.Trigger.DEAL_CREATED,
            build_deal_context(deal, trigger=AutomationRule.Trigger.DEAL_CREATED),
        )
        try:
            from process.events import dispatch_domain_event

            dispatch_domain_event(
                workspace,
                "deal.created",
                {
                    "deal_id": deal.id,
                    "organization_id": deal.organization_id,
                    "project_id": deal.project_id,
                    "user_id": request.user.id,
                    "business_key": f"deal:{deal.id}",
                },
            )
        except Exception:  # noqa: BLE001
            pass
        deal = _deal_queryset(workspace).get(pk=deal.pk)
        return Response(DealSerializer(deal).data, status=status.HTTP_201_CREATED)


class DealDetailView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get_object(self, deal_id):
        return get_object_or_404(_deal_queryset(self.get_workspace()), pk=deal_id)

    def get(self, request, deal_id):
        return Response(DealSerializer(self.get_object(deal_id)).data)

    def patch(self, request, deal_id):
        workspace = self.get_workspace()
        deal = self.get_object(deal_id)
        serializer = DealWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if "title" in data:
            deal.title = data["title"]
        if "amount" in data:
            deal.amount = data["amount"]
        if "probability" in data:
            deal.probability = data["probability"]
        if "close_date" in request.data:
            deal.close_date = data.get("close_date")
        if "notes" in data:
            deal.notes = data["notes"]
        if "position" in data:
            deal.position = data["position"]
        if "stage_id" in data:
            stage = get_object_or_404(
                PipelineStage.objects.filter(pipeline=deal.pipeline),
                pk=data["stage_id"],
            )
            deal.stage = stage
            if "probability" not in data:
                deal.probability = stage.default_probability
        if "organization_id" in request.data:
            org_id = data.get("organization_id")
            deal.organization = (
                get_object_or_404(
                    Organization.objects.filter(workspace=workspace), pk=org_id
                )
                if org_id
                else None
            )
        if "person_id" in request.data:
            person_id = data.get("person_id")
            deal.person = (
                get_object_or_404(
                    Person.objects.filter(workspace=workspace), pk=person_id
                )
                if person_id
                else None
            )
        if "project_id" in request.data:
            project_id = data.get("project_id")
            deal.project = (
                get_object_or_404(
                    Project.objects.filter(workspace=workspace), pk=project_id
                )
                if project_id
                else None
            )
        if "owner_id" in request.data:
            deal.owner = _resolve_owner(workspace, data.get("owner_id"))
        deal.save()
        deal = self.get_object(deal.id)
        return Response(DealSerializer(deal).data)

    def delete(self, request, deal_id):
        self.get_object(deal_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class DealCreateProjectView(WorkspaceMixin, APIView):
    """Create a project (optionally from template) and link it to the deal."""

    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def post(self, request, deal_id):
        self.require_editor()
        deal = get_object_or_404(
            _deal_queryset(self.get_workspace()).select_related("stage", "organization"),
            pk=deal_id,
        )
        template_id = request.data.get("template_id")
        if template_id in ("", None):
            template_id = None
        else:
            try:
                template_id = int(template_id)
            except (TypeError, ValueError) as exc:
                raise ValidationError({"template_id": "Invalid id."}) from exc

        require_won = request.data.get("require_won")
        if require_won is None:
            require_won = False
        else:
            require_won = str(require_won).lower() in ("1", "true", "yes")

        from crm.handoff import create_project_from_deal, serialize_handoff

        deal, project = create_project_from_deal(
            deal,
            user=request.user,
            template_id=template_id,
            require_won=require_won,
        )
        deal = get_object_or_404(_deal_queryset(self.get_workspace()), pk=deal.id)
        return Response(
            serialize_handoff(deal, project),
            status=status.HTTP_201_CREATED,
        )


class DealMoveView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def post(self, request, deal_id):
        workspace = self.get_workspace()
        deal = get_object_or_404(_deal_queryset(workspace), pk=deal_id)
        serializer = DealMoveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        stage = get_object_or_404(
            PipelineStage.objects.filter(pipeline=deal.pipeline),
            pk=data["stage_id"],
        )
        from_stage_id = deal.stage_id
        deal = apply_deal_move(
            deal,
            stage,
            position=data.get("position"),
            probability=data.get("probability"),
        )
        if from_stage_id != deal.stage_id:
            run_automations(
                workspace,
                AutomationRule.Trigger.DEAL_STAGE_CHANGED,
                build_deal_context(
                    deal,
                    trigger=AutomationRule.Trigger.DEAL_STAGE_CHANGED,
                    from_stage_id=from_stage_id,
                ),
            )
            try:
                from process.events import dispatch_domain_event

                dispatch_domain_event(
                    workspace,
                    "deal.stage_changed",
                    {
                        "deal_id": deal.id,
                        "organization_id": deal.organization_id,
                        "project_id": deal.project_id,
                        "from_stage_id": from_stage_id,
                        "stage_id": deal.stage_id,
                        "user_id": request.user.id,
                        "business_key": f"deal:{deal.id}:stage",
                    },
                )
            except Exception:  # noqa: BLE001
                pass
        deal = _deal_queryset(workspace).get(pk=deal.pk)
        return Response(DealSerializer(deal).data)


class DealForecastView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get(self, request):
        workspace = self.get_workspace()
        ensure_default_pipeline(workspace)
        open_deals = Deal.objects.filter(
            workspace=workspace, stage__is_won=False, stage__is_lost=False
        )
        won = Deal.objects.filter(workspace=workspace, stage__is_won=True)
        lost = Deal.objects.filter(workspace=workspace, stage__is_lost=True)

        open_amount = open_deals.aggregate(total=Coalesce(Sum("amount"), Decimal("0")))[
            "total"
        ]
        # Weighted forecast in Python for Decimal precision across probability
        forecast = Decimal("0")
        for deal in open_deals.only("amount", "probability"):
            forecast += (deal.amount * deal.probability) / Decimal("100")
        won_amount = won.aggregate(total=Coalesce(Sum("amount"), Decimal("0")))["total"]
        lost_amount = lost.aggregate(total=Coalesce(Sum("amount"), Decimal("0")))[
            "total"
        ]
        return Response(
            {
                "open_count": open_deals.count(),
                "open_amount": float(open_amount),
                "forecast_amount": float(forecast),
                "won_count": won.count(),
                "won_amount": float(won_amount),
                "lost_count": lost.count(),
                "lost_amount": float(lost_amount),
            }
        )


class DealTaskListCreateView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get_deal(self, deal_id):
        return get_object_or_404(
            Deal.objects.filter(workspace=self.get_workspace()),
            pk=deal_id,
        )

    def get(self, request, deal_id):
        deal = self.get_deal(deal_id)
        tasks = deal.tasks.select_related("assignee")
        return Response(DealTaskSerializer(tasks, many=True).data)

    def post(self, request, deal_id):
        deal = self.get_deal(deal_id)
        serializer = DealTaskWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if not data.get("title"):
            raise ValidationError({"title": "This field is required."})
        assignee = None
        if "assignee_id" in data:
            assignee = _resolve_owner(self.get_workspace(), data.get("assignee_id"))
        task = DealTask.objects.create(
            deal=deal,
            title=data["title"],
            due_date=data.get("due_date"),
            is_done=data.get("is_done", False),
            priority=data.get("priority", DealTask.Priority.NORMAL),
            board_status=(
                DealTask.BoardStatus.DONE
                if data.get("is_done")
                else data.get("board_status", DealTask.BoardStatus.TODO)
            ),
            checklist=normalize_checklist(
                request.data.get("checklist", data.get("checklist"))
            ),
            repeat=data.get("repeat", DealTask.Repeat.NONE),
            assignee=assignee,
            remind_before_days=data.get("remind_before_days", 1),
            notes=data.get("notes", ""),
        )
        if task.is_done:
            task.board_status = DealTask.BoardStatus.DONE
            task.save(update_fields=["board_status"])
        return Response(
            DealTaskSerializer(task).data, status=status.HTTP_201_CREATED
        )


class DealTaskDetailView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get_task(self, deal_id, task_id):
        return get_object_or_404(
            DealTask.objects.filter(
                deal_id=deal_id, deal__workspace=self.get_workspace()
            ),
            pk=task_id,
        )

    def patch(self, request, deal_id, task_id):
        task = self.get_task(deal_id, task_id)
        serializer = DealTaskWriteSerializer(
            data={**request.data, "title": request.data.get("title", task.title)}
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if "assignee_id" in request.data:
            task.assignee = _resolve_owner(
                self.get_workspace(), data.get("assignee_id")
            )
        apply_task_fields(task, data, request_data=request.data)
        return Response(DealTaskSerializer(task).data)

    def delete(self, request, deal_id, task_id):
        self.get_task(deal_id, task_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
