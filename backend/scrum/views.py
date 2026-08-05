"""Scrum API views — project-scoped Product Backlog and Sprints."""

from __future__ import annotations

from datetime import date, timedelta

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from projects.views import WorkspaceMixin
from scrum.models import ProductBacklogItem, ScrumSprint
from scrum.serializers import (
    ProductBacklogItemSerializer,
    ProductBacklogItemWriteSerializer,
    ScrumSprintSerializer,
    ScrumSprintWriteSerializer,
)
from workspaces.mixins import IsWorkspaceEditorOrReadOnly


class ProjectScopedMixin(WorkspaceMixin):
    def get_project(self, project_id):
        return get_object_or_404(self.get_project_queryset(), pk=project_id)


class ProductBacklogListCreateView(ProjectScopedMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get(self, request, project_id):
        project = self.get_project(project_id)
        qs = project.scrum_pbis.select_related("assignee", "sprint").all()
        scope = request.query_params.get("scope")
        if scope == "product":
            qs = qs.filter(sprint__isnull=True)
        elif scope == "committed":
            qs = qs.filter(sprint__isnull=False)
        return Response(ProductBacklogItemSerializer(qs, many=True).data)

    def post(self, request, project_id):
        project = self.get_project(project_id)
        serializer = ProductBacklogItemWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if "rank" not in serializer.validated_data:
            max_rank = (
                project.scrum_pbis.order_by("-rank").values_list("rank", flat=True).first()
                or 0
            )
            serializer.validated_data["rank"] = max_rank + 10
        item = serializer.save(project=project, created_by=request.user)
        return Response(
            ProductBacklogItemSerializer(item).data, status=status.HTTP_201_CREATED
        )


class ProductBacklogItemDetailView(ProjectScopedMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get_item(self, pbi_id):
        return get_object_or_404(
            ProductBacklogItem.objects.filter(
                project__workspace=self.get_workspace()
            ).select_related("assignee", "sprint"),
            pk=pbi_id,
        )

    def patch(self, request, pbi_id):
        item = self.get_item(pbi_id)
        serializer = ProductBacklogItemWriteSerializer(
            item, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(ProductBacklogItemSerializer(item).data)

    def delete(self, request, pbi_id):
        self.get_item(pbi_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ScrumSprintListCreateView(ProjectScopedMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get(self, request, project_id):
        project = self.get_project(project_id)
        sprints = project.scrum_sprints.prefetch_related("pbis").all()
        return Response(ScrumSprintSerializer(sprints, many=True).data)

    def post(self, request, project_id):
        project = self.get_project(project_id)
        serializer = ScrumSprintWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        sprint = serializer.save(project=project)
        return Response(
            ScrumSprintSerializer(sprint).data, status=status.HTTP_201_CREATED
        )


class ScrumSprintDetailView(ProjectScopedMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get_sprint(self, sprint_id):
        return get_object_or_404(
            ScrumSprint.objects.filter(
                project__workspace=self.get_workspace()
            ).prefetch_related("pbis"),
            pk=sprint_id,
        )

    def get(self, request, sprint_id):
        return Response(ScrumSprintSerializer(self.get_sprint(sprint_id)).data)

    def patch(self, request, sprint_id):
        sprint = self.get_sprint(sprint_id)
        serializer = ScrumSprintWriteSerializer(
            sprint, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(ScrumSprintSerializer(sprint).data)


class ScrumSprintActivateView(ProjectScopedMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def post(self, request, sprint_id):
        sprint = get_object_or_404(
            ScrumSprint.objects.filter(project__workspace=self.get_workspace()),
            pk=sprint_id,
        )
        if not sprint.starts_on or not sprint.ends_on:
            raise ValidationError("Sprint needs starts_on and ends_on to activate.")
        if sprint.ends_on < sprint.starts_on:
            raise ValidationError("ends_on must be on/after starts_on.")
        ScrumSprint.objects.filter(
            project=sprint.project, status=ScrumSprint.Status.ACTIVE
        ).exclude(pk=sprint.id).update(status=ScrumSprint.Status.PLANNED)
        sprint.status = ScrumSprint.Status.ACTIVE
        sprint.save(update_fields=["status", "updated_at"])
        return Response(ScrumSprintSerializer(sprint).data)


class ScrumSprintCompleteView(ProjectScopedMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def post(self, request, sprint_id):
        sprint = get_object_or_404(
            ScrumSprint.objects.filter(project__workspace=self.get_workspace()),
            pk=sprint_id,
        )
        sprint.status = ScrumSprint.Status.COMPLETED
        sprint.save(update_fields=["status", "updated_at"])
        return Response(ScrumSprintSerializer(sprint).data)


class ScrumSprintCommitView(ProjectScopedMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def post(self, request, sprint_id):
        sprint = get_object_or_404(
            ScrumSprint.objects.filter(project__workspace=self.get_workspace()),
            pk=sprint_id,
        )
        if sprint.status == ScrumSprint.Status.COMPLETED:
            raise ValidationError("Cannot commit to a completed sprint.")
        pbi_ids = request.data.get("pbi_ids") or []
        if not isinstance(pbi_ids, list):
            raise ValidationError({"pbi_ids": "Must be a list of ids."})
        updated = ProductBacklogItem.objects.filter(
            project=sprint.project, pk__in=pbi_ids
        ).update(sprint=sprint)
        return Response({"committed": updated, "sprint_id": sprint.id})


class ScrumSprintBacklogView(ProjectScopedMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get(self, request, sprint_id):
        sprint = get_object_or_404(
            ScrumSprint.objects.filter(project__workspace=self.get_workspace()),
            pk=sprint_id,
        )
        items = sprint.pbis.select_related("assignee").all()
        return Response(ProductBacklogItemSerializer(items, many=True).data)


class ScrumSprintBurndownView(ProjectScopedMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get(self, request, sprint_id):
        sprint = get_object_or_404(
            ScrumSprint.objects.filter(project__workspace=self.get_workspace())
            .prefetch_related("pbis"),
            pk=sprint_id,
        )
        pbis = list(sprint.pbis.all())
        committed = sum(p.story_points or 0 for p in pbis)
        remaining_now = sum(
            p.story_points or 0
            for p in pbis
            if p.status != ProductBacklogItem.Status.DONE
        )
        starts = sprint.starts_on or date.today()
        ends = sprint.ends_on or starts
        if ends < starts:
            ends = starts
        days = (ends - starts).days
        series = []
        for i in range(days + 1):
            day = starts + timedelta(days=i)
            ideal = (
                committed
                if days == 0
                else max(0, round(committed * (1 - i / days), 1))
            )
            # MVP: remaining is constant until Done; approximate with current for today+
            remaining = remaining_now if day <= date.today() else remaining_now
            if day > date.today():
                remaining = remaining_now
            series.append(
                {
                    "date": day.isoformat(),
                    "remaining": remaining if day <= date.today() else None,
                    "ideal": ideal,
                }
            )
        # For past days without snapshots, show remaining_now on today only
        for row in series:
            if row["date"] == date.today().isoformat():
                row["remaining"] = remaining_now
            elif row["date"] < date.today().isoformat():
                # no history: leave null or use committed until we have snapshots
                row["remaining"] = None
        return Response(
            {
                "sprint_id": sprint.id,
                "committed_points": committed,
                "remaining_points": remaining_now,
                "burndown": series,
            }
        )
