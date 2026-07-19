from datetime import date

from django.db.models import Sum
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.services import log_audit
from projects.cpm import compute_critical_path, compute_evm_lite
from projects.models import (
    ActivityDependency,
    Project,
    ProjectCharter,
    ProjectTemplate,
    ScheduleActivity,
    WBSNode,
)
from projects.calendar import project_milestone_events, workspace_milestone_events
from projects.exports import workspace_calendar_ics
from projects.serializers import (
    ActivityDependencySerializer,
    ActivityDependencyWriteSerializer,
    ProjectListSerializer,
    ProjectTemplateSerializer,
    ProjectWriteSerializer,
    ScheduleActivitySerializer,
    ScheduleActivityUpdateSerializer,
    WBSNodeUpdateSerializer,
    WBSNodeWriteSerializer,
)
from projects.serializers_pmbok import ProjectCharterSerializer, RiskSerializer
from projects.services import build_wbs_tree, create_work_package
from projects.sync import sync_card_from_activity
from projects.templates import apply_project_template, capture_project_template
from workspaces.events import publish_event
from workspaces.mixins import IsWorkspaceEditorOrReadOnly, WorkspaceMixin as BaseWorkspaceMixin


class WorkspaceMixin(BaseWorkspaceMixin):
    def get_project_queryset(self):
        return Project.objects.filter(workspace=self.get_workspace()).select_related(
            "board"
        )

    def get_wbs_queryset(self):
        return WBSNode.objects.filter(project__workspace=self.get_workspace())

    def get_activity_queryset(self):
        return ScheduleActivity.objects.filter(
            wbs_node__project__workspace=self.get_workspace()
        )


class ProjectListCreateView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get(self, request):
        projects = self.get_project_queryset()
        return Response(ProjectListSerializer(projects, many=True).data)

    def post(self, request):
        serializer = ProjectWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        template_id = serializer.validated_data.pop("template_id", None)
        workspace = self.get_workspace()
        project = Project.objects.create(
            workspace=workspace,
            manager=request.user,
            **serializer.validated_data,
        )
        if template_id:
            template = get_object_or_404(
                ProjectTemplate,
                pk=template_id,
                workspace=workspace,
            )
            apply_project_template(project, template)
        return Response(
            ProjectListSerializer(project).data,
            status=status.HTTP_201_CREATED,
        )


class ProjectTemplateListCreateView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get(self, request):
        templates = ProjectTemplate.objects.filter(workspace=self.get_workspace())
        return Response(ProjectTemplateSerializer(templates, many=True).data)

    def post(self, request):
        name = str(request.data.get("name", "")).strip()
        if not name:
            raise ValidationError({"name": "Template name is required."})
        workspace = self.get_workspace()
        if ProjectTemplate.objects.filter(workspace=workspace, name=name).exists():
            raise ValidationError({"name": "Template name must be unique."})
        source_project = get_object_or_404(
            self.get_project_queryset(),
            pk=request.data.get("source_project_id"),
        )
        template = capture_project_template(
            source_project,
            name=name,
            description=str(request.data.get("description", "")).strip(),
            created_by=request.user,
        )
        return Response(
            ProjectTemplateSerializer(template).data,
            status=status.HTTP_201_CREATED,
        )


class ProjectTemplateDetailView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def delete(self, request, template_id):
        template = get_object_or_404(
            ProjectTemplate,
            workspace=self.get_workspace(),
            pk=template_id,
        )
        template.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProjectDetailView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get_project(self, project_id):
        return get_object_or_404(self.get_project_queryset(), pk=project_id)

    def get(self, request, project_id):
        project = self.get_project(project_id)
        return Response(ProjectListSerializer(project).data)

    def patch(self, request, project_id):
        project = self.get_project(project_id)
        serializer = ProjectWriteSerializer(project, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(ProjectListSerializer(project).data)

    def delete(self, request, project_id):
        project = self.get_project(project_id)
        project.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProjectDashboardView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get(self, request, project_id):
        project = get_object_or_404(
            self.get_project_queryset().select_related("charter"),
            pk=project_id,
        )
        activities = list(
            ScheduleActivity.objects.filter(wbs_node__project=project).select_related(
                "wbs_node"
            )
        )
        milestones = [a for a in activities if a.is_milestone][:5]
        avg_progress = 0
        if activities:
            avg_progress = round(sum(a.progress for a in activities) / len(activities))

        from finance.models import Transaction

        actual_cost = float(
            Transaction.objects.filter(
                project=project,
                transaction_type=Transaction.TransactionType.EXPENSE,
            ).aggregate(total=Sum("amount"))["total"]
            or 0
        )
        cpm = compute_critical_path(project)
        charter = getattr(project, "charter", None)
        top_risks = project.risks.all()[:3]

        return Response(
            {
                "project_id": project.id,
                "name": project.name,
                "status": project.status,
                "progress": avg_progress,
                "wbs_count": project.wbs_nodes.count(),
                "budget": float(project.budget or 0),
                "upcoming_milestones": ScheduleActivitySerializer(
                    milestones, many=True
                ).data,
                "charter": ProjectCharterSerializer(charter).data if charter else None,
                "top_risks": RiskSerializer(top_risks, many=True).data,
                "evm": compute_evm_lite(project, activities, actual_cost),
                "critical_path": {
                    "project_duration": cpm["project_duration"],
                    "critical_count": len(cpm["critical_path_ids"]),
                    "critical_path_ids": cpm["critical_path_ids"],
                },
            }
        )


class WBSTreeView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get(self, request, project_id):
        project = get_object_or_404(self.get_project_queryset(), pk=project_id)
        nodes = (
            project.wbs_nodes.select_related(
                "schedule", "card", "tracker", "workflow_status", "assignee"
            )
            .order_by("position", "id")
        )
        return Response(build_wbs_tree(list(nodes)))

    def post(self, request, project_id):
        project = get_object_or_404(self.get_project_queryset(), pk=project_id)
        serializer = WBSNodeWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        parent = None
        if data.get("parent_id"):
            parent = get_object_or_404(project.wbs_nodes, pk=data["parent_id"])
        elif project.wbs_nodes.filter(parent__isnull=True).exists():
            parent = project.wbs_nodes.filter(parent__isnull=True).first()

        if parent is None:
            raise ValidationError({"parent_id": "Parent WBS node is required."})

        node = create_work_package(
            project,
            parent,
            data["title"],
            data.get("node_type", WBSNode.NodeType.WORK_PACKAGE),
        )
        if data.get("description"):
            node.description = data["description"]
            node.save(update_fields=["description"])

        log_audit(
            project.workspace,
            request.user,
            "wbs.create",
            "WBSNode",
            node.id,
            summary=f"Created WBS node {node.code} {node.title}",
            changes={"title": node.title, "node_type": node.node_type},
        )

        nodes = (
            project.wbs_nodes.select_related(
                "schedule", "card", "tracker", "workflow_status", "assignee"
            )
            .order_by("position", "id")
        )
        return Response(
            build_wbs_tree(list(nodes)),
            status=status.HTTP_201_CREATED,
        )


class WBSNodeDetailView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get_node(self, wbs_id):
        return get_object_or_404(self.get_wbs_queryset(), pk=wbs_id)

    def patch(self, request, wbs_id):
        node = self.get_node(wbs_id)
        serializer = WBSNodeUpdateSerializer(node, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        log_audit(
            node.project.workspace,
            request.user,
            "wbs.update",
            "WBSNode",
            node.id,
            summary=f"Updated WBS node {node.code} {node.title}",
            changes={
                key: value
                for key, value in request.data.items()
                if key != "custom_values"
            },
        )
        publish_event(
            node.project.workspace_id,
            "wbs.updated",
            {"wbs_id": node.id, "project_id": node.project_id},
        )
        nodes = (
            node.project.wbs_nodes.select_related("schedule", "card")
            .order_by("position", "id")
        )
        return Response(build_wbs_tree(list(nodes)))

    def delete(self, request, wbs_id):
        node = self.get_node(wbs_id)
        if node.parent_id is None:
            raise ValidationError("Root WBS node cannot be deleted.")
        log_audit(
            node.project.workspace,
            request.user,
            "wbs.delete",
            "WBSNode",
            node.id,
            summary=f"Deleted WBS node {node.code} {node.title}",
            changes={"title": node.title},
        )
        node.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProjectScheduleView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get(self, request, project_id):
        project = get_object_or_404(self.get_project_queryset(), pk=project_id)
        activities = (
            ScheduleActivity.objects.filter(wbs_node__project=project)
            .select_related("wbs_node")
            .prefetch_related(
                Prefetch(
                    "successor_links",
                    queryset=ActivityDependency.objects.select_related(
                        "successor", "predecessor"
                    ),
                )
            )
        )
        dependencies = ActivityDependency.objects.filter(
            predecessor__wbs_node__project=project,
            successor__wbs_node__project=project,
        )
        return Response(
            {
                "activities": ScheduleActivitySerializer(activities, many=True).data,
                "dependencies": ActivityDependencySerializer(
                    dependencies, many=True
                ).data,
            }
        )


class ScheduleActivityDetailView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def patch(self, request, activity_id):
        activity = get_object_or_404(self.get_activity_queryset(), pk=activity_id)
        serializer = ScheduleActivityUpdateSerializer(
            activity, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        if "progress" in request.data:
            sync_card_from_activity(activity)

        return Response(ScheduleActivitySerializer(activity).data)


class ActivityDependencyCreateView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def post(self, request, project_id):
        project = get_object_or_404(self.get_project_queryset(), pk=project_id)
        serializer = ActivityDependencyWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        predecessor = get_object_or_404(
            self.get_activity_queryset(),
            pk=data["predecessor_id"],
            wbs_node__project=project,
        )
        successor = get_object_or_404(
            self.get_activity_queryset(),
            pk=data["successor_id"],
            wbs_node__project=project,
        )
        if predecessor.pk == successor.pk:
            raise ValidationError("Activity cannot depend on itself.")

        dependency = ActivityDependency.objects.create(
            predecessor=predecessor,
            successor=successor,
            dependency_type=data["dependency_type"],
            lag_days=data["lag_days"],
        )
        return Response(
            ActivityDependencySerializer(dependency).data,
            status=status.HTTP_201_CREATED,
        )


def _parse_year_month(request):
    try:
        year = int(request.query_params.get("year", date.today().year))
        month = int(request.query_params.get("month", date.today().month))
    except (TypeError, ValueError):
        raise ValidationError("Invalid year or month.")
    return year, month


class ProjectCalendarView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get(self, request, project_id):
        project = get_object_or_404(self.get_project_queryset(), pk=project_id)
        year, month = _parse_year_month(request)
        return Response(project_milestone_events(project, year, month))


class WorkspaceMilestonesCalendarView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get(self, request):
        year, month = _parse_year_month(request)
        return Response(
            workspace_milestone_events(self.get_workspace(), year, month)
        )


class WorkspaceCalendarIcsView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get(self, request):
        return workspace_calendar_ics(self.get_workspace())
