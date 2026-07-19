from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.services import log_audit
from projects.baseline import create_baseline
from projects.cpm import compute_critical_path
from projects.exports import (
    project_milestones_ics,
    render_wbs_csv,
    render_wbs_xlsx,
)
from projects.models import (
    ProjectBaseline,
    ProjectCharter,
    RACIEntry,
    Risk,
    Stakeholder,
)
from projects.pdf import render_status_report_pdf
from projects.reports import build_status_report
from projects.serializers_pmbok import (
    ProjectBaselineSerializer,
    ProjectCharterSerializer,
    RACIEntrySerializer,
    RACIWriteSerializer,
    RiskSerializer,
    RiskWriteSerializer,
    StakeholderSerializer,
    StakeholderWriteSerializer,
)
from projects.views import WorkspaceMixin
from workspaces.mixins import IsWorkspaceEditorOrReadOnly
from workspaces.webhooks import emit_webhook


class RiskListCreateView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get(self, request, project_id):
        project = get_object_or_404(self.get_project_queryset(), pk=project_id)
        risks = project.risks.all()
        return Response(RiskSerializer(risks, many=True).data)

    def post(self, request, project_id):
        project = get_object_or_404(self.get_project_queryset(), pk=project_id)
        serializer = RiskWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        risk = Risk.objects.create(project=project, **serializer.validated_data)
        log_audit(
            project.workspace,
            request.user,
            "risk.create",
            "Risk",
            risk.id,
            summary=f"Created risk: {risk.title}",
            changes={"title": risk.title, "probability": risk.probability, "impact": risk.impact},
        )
        emit_webhook(
            project.workspace,
            "risk.created",
            {
                "risk_id": risk.id,
                "project_id": project.id,
                "title": risk.title,
                "probability": risk.probability,
                "impact": risk.impact,
                "status": risk.status,
            },
        )
        return Response(RiskSerializer(risk).data, status=status.HTTP_201_CREATED)


class RiskDetailView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get_risk(self, risk_id):
        return get_object_or_404(
            Risk.objects.filter(project__workspace=self.get_workspace()),
            pk=risk_id,
        )

    def patch(self, request, risk_id):
        risk = self.get_risk(risk_id)
        serializer = RiskWriteSerializer(risk, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        log_audit(
            risk.project.workspace,
            request.user,
            "risk.update",
            "Risk",
            risk.id,
            summary=f"Updated risk: {risk.title}",
            changes={key: request.data[key] for key in request.data},
        )
        emit_webhook(
            risk.project.workspace,
            "risk.updated",
            {
                "risk_id": risk.id,
                "project_id": risk.project_id,
                "title": risk.title,
                "probability": risk.probability,
                "impact": risk.impact,
                "status": risk.status,
            },
        )
        return Response(RiskSerializer(risk).data)

    def delete(self, request, risk_id):
        risk = self.get_risk(risk_id)
        log_audit(
            risk.project.workspace,
            request.user,
            "risk.delete",
            "Risk",
            risk.id,
            summary=f"Deleted risk: {risk.title}",
            changes={"title": risk.title},
        )
        emit_webhook(
            risk.project.workspace,
            "risk.deleted",
            {
                "risk_id": risk.id,
                "project_id": risk.project_id,
                "title": risk.title,
            },
        )
        risk.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class StakeholderListCreateView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get(self, request, project_id):
        project = get_object_or_404(self.get_project_queryset(), pk=project_id)
        return Response(StakeholderSerializer(project.stakeholders.all(), many=True).data)

    def post(self, request, project_id):
        project = get_object_or_404(self.get_project_queryset(), pk=project_id)
        serializer = StakeholderWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        stakeholder = Stakeholder.objects.create(
            project=project, **serializer.validated_data
        )
        return Response(
            StakeholderSerializer(stakeholder).data,
            status=status.HTTP_201_CREATED,
        )


class StakeholderDetailView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get_stakeholder(self, stakeholder_id):
        return get_object_or_404(
            Stakeholder.objects.filter(project__workspace=self.get_workspace()),
            pk=stakeholder_id,
        )

    def patch(self, request, stakeholder_id):
        stakeholder = self.get_stakeholder(stakeholder_id)
        serializer = StakeholderWriteSerializer(
            stakeholder, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(StakeholderSerializer(stakeholder).data)

    def delete(self, request, stakeholder_id):
        stakeholder = self.get_stakeholder(stakeholder_id)
        stakeholder.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProjectCharterView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get(self, request, project_id):
        project = get_object_or_404(self.get_project_queryset(), pk=project_id)
        charter = getattr(project, "charter", None)
        if charter is None:
            return Response(
                {
                    "project": project.id,
                    "vision": "",
                    "objectives": "",
                    "scope": "",
                    "success_criteria": "",
                    "assumptions": "",
                    "constraints": "",
                }
            )
        return Response(ProjectCharterSerializer(charter).data)

    def patch(self, request, project_id):
        project = get_object_or_404(self.get_project_queryset(), pk=project_id)
        charter, _ = ProjectCharter.objects.get_or_create(project=project)
        serializer = ProjectCharterSerializer(charter, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(ProjectCharterSerializer(charter).data)


class RACIListCreateView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get(self, request, project_id):
        project = get_object_or_404(self.get_project_queryset(), pk=project_id)
        entries = RACIEntry.objects.filter(wbs_node__project=project).select_related(
            "wbs_node", "stakeholder"
        )
        return Response(RACIEntrySerializer(entries, many=True).data)

    def post(self, request, project_id):
        project = get_object_or_404(self.get_project_queryset(), pk=project_id)
        serializer = RACIWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        wbs_node = get_object_or_404(project.wbs_nodes, pk=data["wbs_node_id"])
        stakeholder = get_object_or_404(project.stakeholders, pk=data["stakeholder_id"])
        entry, created = RACIEntry.objects.update_or_create(
            wbs_node=wbs_node,
            stakeholder=stakeholder,
            defaults={"raci_type": data["raci_type"]},
        )
        status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(RACIEntrySerializer(entry).data, status=status_code)


class RACIDetailView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def delete(self, request, raci_id):
        entry = get_object_or_404(
            RACIEntry.objects.filter(wbs_node__project__workspace=self.get_workspace()),
            pk=raci_id,
        )
        entry.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class BaselineListCreateView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get(self, request, project_id):
        project = get_object_or_404(self.get_project_queryset(), pk=project_id)
        baselines = project.baselines.prefetch_related("activities")
        return Response(ProjectBaselineSerializer(baselines, many=True).data)

    def post(self, request, project_id):
        project = get_object_or_404(self.get_project_queryset(), pk=project_id)
        name = request.data.get("name", "").strip() or f"Baseline {project.baselines.count() + 1}"
        baseline = create_baseline(project, name, request.user)
        return Response(
            ProjectBaselineSerializer(baseline).data,
            status=status.HTTP_201_CREATED,
        )


class BaselineDetailView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get_baseline(self, baseline_id):
        return get_object_or_404(
            ProjectBaseline.objects.filter(project__workspace=self.get_workspace()),
            pk=baseline_id,
        )

    def get(self, request, baseline_id):
        baseline = self.get_baseline(baseline_id)
        return Response(ProjectBaselineSerializer(baseline).data)

    def patch(self, request, baseline_id):
        baseline = self.get_baseline(baseline_id)
        name = str(request.data.get("name", "")).strip()
        if not name:
            raise ValidationError({"name": "Name is required."})
        baseline.name = name
        baseline.save(update_fields=["name"])
        return Response(ProjectBaselineSerializer(baseline).data)

    def delete(self, request, baseline_id):
        baseline = self.get_baseline(baseline_id)
        baseline.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CriticalPathView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get(self, request, project_id):
        project = get_object_or_404(self.get_project_queryset(), pk=project_id)
        return Response(compute_critical_path(project))


class ProjectExportView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get(self, request, project_id):
        project = get_object_or_404(self.get_project_queryset(), pk=project_id)
        fmt = (request.query_params.get("output") or "json").lower()
        if fmt == "csv":
            return render_wbs_csv(project)
        if fmt == "xlsx":
            return render_wbs_xlsx(project)
        report = build_status_report(project)
        if fmt == "pdf":
            pdf_bytes = render_status_report_pdf(report)
            response = HttpResponse(pdf_bytes, content_type="application/pdf")
            response["Content-Disposition"] = (
                f'attachment; filename="project-{project.id}-status.pdf"'
            )
            return response
        return Response(report)


class ProjectMilestonesIcsView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get(self, request, project_id):
        project = get_object_or_404(self.get_project_queryset(), pk=project_id)
        return project_milestones_ics(project)
