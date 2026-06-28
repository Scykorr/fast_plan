from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from projects.models import ActivityDependency, Project, ScheduleActivity, WBSNode
from projects.serializers import (
    ActivityDependencySerializer,
    ActivityDependencyWriteSerializer,
    ProjectListSerializer,
    ProjectWriteSerializer,
    ScheduleActivitySerializer,
    ScheduleActivityUpdateSerializer,
    WBSNodeUpdateSerializer,
    WBSNodeWriteSerializer,
)
from projects.services import build_wbs_tree, create_work_package
from workspaces.services import get_user_workspace


class WorkspaceMixin:
    def get_workspace(self):
        workspace = get_user_workspace(self.request.user)
        if workspace is None:
            raise NotFound("Workspace not found.")
        return workspace

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
    def get(self, request):
        projects = self.get_project_queryset()
        return Response(ProjectListSerializer(projects, many=True).data)

    def post(self, request):
        serializer = ProjectWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        project = Project.objects.create(
            workspace=self.get_workspace(),
            manager=request.user,
            **serializer.validated_data,
        )
        return Response(
            ProjectListSerializer(project).data,
            status=status.HTTP_201_CREATED,
        )


class ProjectDetailView(WorkspaceMixin, APIView):
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
    def get(self, request, project_id):
        project = get_object_or_404(self.get_project_queryset(), pk=project_id)
        activities = ScheduleActivity.objects.filter(wbs_node__project=project)
        milestones = activities.filter(is_milestone=True).order_by("start_date")[:5]
        avg_progress = 0
        if activities.exists():
            avg_progress = round(sum(a.progress for a in activities) / activities.count())

        return Response(
            {
                "project_id": project.id,
                "name": project.name,
                "status": project.status,
                "progress": avg_progress,
                "wbs_count": project.wbs_nodes.count(),
                "upcoming_milestones": ScheduleActivitySerializer(
                    milestones, many=True
                ).data,
            }
        )


class WBSTreeView(WorkspaceMixin, APIView):
    def get(self, request, project_id):
        project = get_object_or_404(self.get_project_queryset(), pk=project_id)
        nodes = (
            project.wbs_nodes.select_related("schedule")
            .select_related("card")
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

        nodes = (
            project.wbs_nodes.select_related("schedule", "card")
            .order_by("position", "id")
        )
        return Response(
            build_wbs_tree(list(nodes)),
            status=status.HTTP_201_CREATED,
        )


class WBSNodeDetailView(WorkspaceMixin, APIView):
    def get_node(self, wbs_id):
        return get_object_or_404(self.get_wbs_queryset(), pk=wbs_id)

    def patch(self, request, wbs_id):
        node = self.get_node(wbs_id)
        serializer = WBSNodeUpdateSerializer(node, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        nodes = (
            node.project.wbs_nodes.select_related("schedule", "card")
            .order_by("position", "id")
        )
        return Response(build_wbs_tree(list(nodes)))

    def delete(self, request, wbs_id):
        node = self.get_node(wbs_id)
        if node.parent_id is None:
            raise ValidationError("Root WBS node cannot be deleted.")
        node.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProjectScheduleView(WorkspaceMixin, APIView):
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
    def patch(self, request, activity_id):
        activity = get_object_or_404(self.get_activity_queryset(), pk=activity_id)
        serializer = ScheduleActivityUpdateSerializer(
            activity, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        card = getattr(activity.wbs_node, "card", None)
        if card and "progress" in request.data:
            board = card.column.board
            columns = list(board.columns.order_by("position", "id"))
            if len(columns) >= 3:
                progress = activity.progress
                if progress >= 100:
                    card.column = columns[2]
                elif progress > 0:
                    card.column = columns[1]
                else:
                    card.column = columns[0]
                card.save(update_fields=["column"])

        return Response(ScheduleActivitySerializer(activity).data)


class ActivityDependencyCreateView(WorkspaceMixin, APIView):
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
