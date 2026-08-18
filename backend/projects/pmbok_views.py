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
    PhaseGate,
    Project,
    ProjectBaseline,
    ProjectChangeRequest,
    ProjectCharter,
    ProjectIssue,
    ProjectLessonsLearned,
    RACIEntry,
    Risk,
    Stakeholder,
    WBSNode,
    WBSQualityCheckItem,
)
from projects.pdf import render_lessons_learned_pdf, render_status_report_pdf
from projects.reports import build_status_report
from projects.serializers_pmbok import (
    PhaseGateSerializer,
    ProjectBaselineSerializer,
    ProjectChangeRequestSerializer,
    ProjectCharterSerializer,
    ProjectIssueSerializer,
    ProjectIssueWriteSerializer,
    ProjectLessonsLearnedSerializer,
    RACIEntrySerializer,
    RACIWriteSerializer,
    RiskSerializer,
    RiskWriteSerializer,
    StakeholderSerializer,
    StakeholderWriteSerializer,
    WBSQualityCheckItemSerializer,
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


class ProjectIssueListCreateView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get(self, request, project_id):
        project = get_object_or_404(self.get_project_queryset(), pk=project_id)
        issues = project.issues.select_related("owner", "related_risk").all()
        return Response(ProjectIssueSerializer(issues, many=True).data)

    def post(self, request, project_id):
        project = get_object_or_404(self.get_project_queryset(), pk=project_id)
        serializer = ProjectIssueWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        issue = serializer.save(project=project)
        log_audit(
            project.workspace,
            request.user,
            "issue.create",
            "ProjectIssue",
            issue.id,
            summary=f"Created issue: {issue.title}",
            changes={
                "title": issue.title,
                "priority": issue.priority,
                "status": issue.status,
            },
        )
        emit_webhook(
            project.workspace,
            "issue.created",
            {
                "issue_id": issue.id,
                "project_id": project.id,
                "title": issue.title,
                "priority": issue.priority,
                "status": issue.status,
            },
        )
        return Response(
            ProjectIssueSerializer(issue).data, status=status.HTTP_201_CREATED
        )


class ProjectIssueDetailView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get_issue(self, issue_id):
        return get_object_or_404(
            ProjectIssue.objects.filter(
                project__workspace=self.get_workspace()
            ).select_related("owner", "related_risk"),
            pk=issue_id,
        )

    def patch(self, request, issue_id):
        issue = self.get_issue(issue_id)
        serializer = ProjectIssueWriteSerializer(
            issue, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        log_audit(
            issue.project.workspace,
            request.user,
            "issue.update",
            "ProjectIssue",
            issue.id,
            summary=f"Updated issue: {issue.title}",
            changes={key: request.data[key] for key in request.data},
        )
        emit_webhook(
            issue.project.workspace,
            "issue.updated",
            {
                "issue_id": issue.id,
                "project_id": issue.project_id,
                "title": issue.title,
                "priority": issue.priority,
                "status": issue.status,
            },
        )
        return Response(ProjectIssueSerializer(issue).data)

    def delete(self, request, issue_id):
        issue = self.get_issue(issue_id)
        log_audit(
            issue.project.workspace,
            request.user,
            "issue.delete",
            "ProjectIssue",
            issue.id,
            summary=f"Deleted issue: {issue.title}",
            changes={"title": issue.title},
        )
        emit_webhook(
            issue.project.workspace,
            "issue.deleted",
            {
                "issue_id": issue.id,
                "project_id": issue.project_id,
                "title": issue.title,
            },
        )
        issue.delete()
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


class ProjectLessonsLearnedView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get(self, request, project_id):
        project = get_object_or_404(self.get_project_queryset(), pk=project_id)
        lessons, _ = ProjectLessonsLearned.objects.get_or_create(project=project)
        return Response(ProjectLessonsLearnedSerializer(lessons).data)

    def patch(self, request, project_id):
        project = get_object_or_404(self.get_project_queryset(), pk=project_id)
        lessons, _ = ProjectLessonsLearned.objects.get_or_create(project=project)
        serializer = ProjectLessonsLearnedSerializer(
            lessons, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(ProjectLessonsLearnedSerializer(lessons).data)


class ProjectLessonsLearnedExportView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get(self, request, project_id):
        project = get_object_or_404(self.get_project_queryset(), pk=project_id)
        lessons, _ = ProjectLessonsLearned.objects.get_or_create(project=project)
        output = (request.query_params.get("output") or "md").lower()
        payload = {
            "project_name": project.name,
            "project_status": project.status,
            **ProjectLessonsLearnedSerializer(lessons).data,
        }
        if output == "pdf":
            pdf = render_lessons_learned_pdf(payload)
            response = HttpResponse(pdf, content_type="application/pdf")
            response["Content-Disposition"] = (
                f'attachment; filename="lessons-{project.id}.pdf"'
            )
            return response
        md = (
            f"# Lessons learned — {project.name}\n\n"
            f"Status: {project.status}\n\n"
            f"## What went well\n\n{lessons.what_went_well or '—'}\n\n"
            f"## What went wrong\n\n{lessons.what_went_wrong or '—'}\n\n"
            f"## Recommendations\n\n{lessons.recommendations or '—'}\n\n"
            f"## Knowledge to reuse\n\n{lessons.knowledge_to_reuse or '—'}\n"
        )
        response = HttpResponse(md, content_type="text/markdown; charset=utf-8")
        response["Content-Disposition"] = (
            f'attachment; filename="lessons-{project.id}.md"'
        )
        return response


class RACIListCreateView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get(self, request, project_id):
        project = get_object_or_404(self.get_project_queryset(), pk=project_id)
        entries = RACIEntry.objects.filter(wbs_node__project=project).select_related(
            "wbs_node", "stakeholder", "obs_role"
        )
        return Response(RACIEntrySerializer(entries, many=True).data)

    def post(self, request, project_id):
        from workspaces.models import ObsRole

        project = get_object_or_404(self.get_project_queryset(), pk=project_id)
        serializer = RACIWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        wbs_node = get_object_or_404(project.wbs_nodes, pk=data["wbs_node_id"])
        stakeholder = None
        if data.get("stakeholder_id"):
            stakeholder = get_object_or_404(
                project.stakeholders, pk=data["stakeholder_id"]
            )
        obs_role = None
        if data.get("obs_role_id"):
            obs_role = get_object_or_404(
                ObsRole.objects.filter(workspace=project.workspace),
                pk=data["obs_role_id"],
            )
        if stakeholder is not None:
            entry, created = RACIEntry.objects.update_or_create(
                wbs_node=wbs_node,
                stakeholder=stakeholder,
                defaults={"raci_type": data["raci_type"], "obs_role": obs_role},
            )
        else:
            entry, created = RACIEntry.objects.update_or_create(
                wbs_node=wbs_node,
                obs_role=obs_role,
                stakeholder=None,
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


class ChangeRequestListCreateView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get(self, request, project_id):
        project = get_object_or_404(self.get_project_queryset(), pk=project_id)
        rows = project.change_requests.select_related(
            "baseline", "requested_by", "decided_by"
        )
        return Response(ProjectChangeRequestSerializer(rows, many=True).data)

    def post(self, request, project_id):
        from projects.change_requests import create_change_request

        project = get_object_or_404(self.get_project_queryset(), pk=project_id)
        cr = create_change_request(
            project,
            title=request.data.get("title"),
            user=request.user,
            description=request.data.get("description"),
            change_type=request.data.get("change_type"),
            status=request.data.get("status") or ProjectChangeRequest.Status.SUBMITTED,
            impact_notes=request.data.get("impact_notes"),
        )
        log_audit(
            project.workspace,
            request.user,
            "change_request.create",
            "ProjectChangeRequest",
            cr.id,
            summary=f"Created CR: {cr.title}",
        )
        return Response(
            ProjectChangeRequestSerializer(cr).data, status=status.HTTP_201_CREATED
        )


class ChangeRequestDetailView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get_object(self, cr_id):
        return get_object_or_404(
            ProjectChangeRequest.objects.filter(
                project__workspace=self.get_workspace()
            ).select_related("baseline", "requested_by", "decided_by"),
            pk=cr_id,
        )

    def get(self, request, cr_id):
        return Response(ProjectChangeRequestSerializer(self.get_object(cr_id)).data)

    def patch(self, request, cr_id):
        cr = self.get_object(cr_id)
        if cr.status not in (
            ProjectChangeRequest.Status.DRAFT,
            ProjectChangeRequest.Status.SUBMITTED,
        ):
            raise ValidationError({"detail": "Only open CRs can be edited."})
        for field in ("title", "description", "impact_notes"):
            if field in request.data:
                setattr(cr, field, str(request.data.get(field) or ""))
        if "change_type" in request.data:
            change_type = request.data.get("change_type")
            if change_type not in ProjectChangeRequest.ChangeType.values:
                raise ValidationError({"change_type": "Invalid change type."})
            cr.change_type = change_type
        if "status" in request.data:
            status_value = request.data.get("status")
            if status_value not in (
                ProjectChangeRequest.Status.DRAFT,
                ProjectChangeRequest.Status.SUBMITTED,
            ):
                raise ValidationError({"status": "Use decide endpoint for approve/reject."})
            cr.status = status_value
        cr.save()
        return Response(ProjectChangeRequestSerializer(cr).data)


class ChangeRequestDecideView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def post(self, request, cr_id):
        from projects.change_requests import decide_change_request

        cr = get_object_or_404(
            ProjectChangeRequest.objects.filter(project__workspace=self.get_workspace()),
            pk=cr_id,
        )
        create_bl = request.data.get("create_baseline", True)
        if isinstance(create_bl, str):
            create_bl = create_bl.lower() not in ("0", "false", "no")
        cr = decide_change_request(
            cr,
            action=request.data.get("action"),
            user=request.user,
            note=request.data.get("note") or "",
            create_baseline_on_approve=bool(create_bl),
        )
        log_audit(
            cr.project.workspace,
            request.user,
            f"change_request.{cr.status}",
            "ProjectChangeRequest",
            cr.id,
            summary=f"CR {cr.status}: {cr.title}",
        )
        return Response(ProjectChangeRequestSerializer(cr).data)


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


class ProjectWaterfallPhasesView(WorkspaceMixin, APIView):
    """List Waterfall L1 phases + gate history; POST seeds SDLC tree."""

    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get(self, request, project_id):
        from projects.waterfall import (
            default_gate_checklist,
            list_project_phases,
            serialize_phase,
        )

        project = get_object_or_404(self.get_project_queryset(), pk=project_id)
        phases = list_project_phases(project)
        gates = (
            PhaseGate.objects.filter(project=project)
            .select_related("wbs_phase_node", "decided_by", "baseline")
            .order_by("-decided_at", "-id")
        )
        return Response(
            {
                "methodology": project.methodology,
                "schedule_locked": project.schedule_locked,
                "default_checklist": default_gate_checklist(),
                "phases": [serialize_phase(p) for p in phases],
                "gates": PhaseGateSerializer(gates, many=True).data,
            }
        )

    def post(self, request, project_id):
        from projects.services import build_wbs_tree
        from projects.waterfall import seed_waterfall_wbs

        project = get_object_or_404(self.get_project_queryset(), pk=project_id)
        replace = bool(request.data.get("replace"))
        seed_waterfall_wbs(project, replace=replace)
        if request.data.get("set_methodology") is True:
            project.methodology = Project.Methodology.PREDICTIVE
            project.save(update_fields=["methodology", "updated_at"])
        nodes = (
            project.wbs_nodes.select_related(
                "schedule", "card", "tracker", "workflow_status", "assignee"
            )
            .order_by("position", "id")
        )
        log_audit(
            project.workspace,
            request.user,
            "waterfall.seed",
            "Project",
            project.id,
            summary="Seeded Waterfall SDLC phases",
        )
        return Response(
            {
                "project": {
                    "id": project.id,
                    "methodology": project.methodology,
                    "schedule_locked": project.schedule_locked,
                },
                "wbs": build_wbs_tree(list(nodes)),
            },
            status=status.HTTP_201_CREATED,
        )


class ProjectPhaseGateDecideView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def post(self, request, project_id):
        from projects.waterfall import decide_phase_gate

        project = get_object_or_404(self.get_project_queryset(), pk=project_id)
        phase_id = request.data.get("wbs_phase_node_id")
        if not phase_id:
            raise ValidationError({"wbs_phase_node_id": "Required."})
        phase = get_object_or_404(
            WBSNode.objects.filter(project=project, phase_order__isnull=False),
            pk=phase_id,
        )
        create_bl = request.data.get("create_baseline", True)
        lock = request.data.get("lock_schedule", True)
        gate = decide_phase_gate(
            project,
            phase,
            decision=request.data.get("decision"),
            user=request.user,
            comment=str(request.data.get("comment") or ""),
            checklist=request.data.get("checklist"),
            create_baseline_on_pass=bool(create_bl),
            lock_schedule_on_pass=bool(lock),
        )
        process_instance_id = request.data.get("process_instance_id")
        if process_instance_id is not None:
            from process.models import ProcessInstance

            instance = ProcessInstance.objects.filter(
                pk=process_instance_id,
                workspace=project.workspace,
            ).first()
            if instance is None:
                raise ValidationError({"process_instance_id": "Not found."})
            gate.process_instance = instance
            gate.save(update_fields=["process_instance"])
        log_audit(
            project.workspace,
            request.user,
            f"phase_gate.{gate.decision}",
            "PhaseGate",
            gate.id,
            summary=f"Phase gate {gate.decision}: {phase.title}",
        )
        project.refresh_from_db()
        return Response(
            {
                "gate": PhaseGateSerializer(gate).data,
                "schedule_locked": project.schedule_locked,
                "phase": {
                    "id": phase.id,
                    "gate_status": phase.gate_status,
                    "phase_key": phase.phase_key,
                },
            }
        )


class ProjectWaterfallPhaseListCreateView(WorkspaceMixin, APIView):
    """POST adds a custom Waterfall phase (append or after another phase)."""

    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def post(self, request, project_id):
        from projects.waterfall import add_waterfall_phase, serialize_phase

        project = get_object_or_404(self.get_project_queryset(), pk=project_id)
        after = request.data.get("after_phase_id")
        phase = add_waterfall_phase(
            project,
            title=str(request.data.get("title") or ""),
            duration_days=int(request.data.get("duration_days") or 10),
            after_phase_id=int(after) if after not in (None, "") else None,
            phase_key=request.data.get("phase_key"),
        )
        log_audit(
            project.workspace,
            request.user,
            "waterfall.phase_add",
            "WBSNode",
            phase.id,
            summary=f"Added Waterfall phase {phase.title}",
        )
        return Response(serialize_phase(phase), status=status.HTTP_201_CREATED)


class ProjectWaterfallPhaseDetailView(WorkspaceMixin, APIView):
    """PATCH rename / DELETE remove a Waterfall phase."""

    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get_phase(self, project, phase_id):
        return get_object_or_404(
            WBSNode.objects.filter(project=project, phase_order__isnull=False),
            pk=phase_id,
        )

    def patch(self, request, project_id, phase_id):
        from projects.waterfall import rename_waterfall_phase, serialize_phase

        project = get_object_or_404(self.get_project_queryset(), pk=project_id)
        phase = self.get_phase(project, phase_id)
        phase = rename_waterfall_phase(
            project, phase, title=str(request.data.get("title") or "")
        )
        log_audit(
            project.workspace,
            request.user,
            "waterfall.phase_rename",
            "WBSNode",
            phase.id,
            summary=f"Renamed Waterfall phase to {phase.title}",
        )
        return Response(serialize_phase(phase))

    def delete(self, request, project_id, phase_id):
        from projects.waterfall import delete_waterfall_phase

        project = get_object_or_404(self.get_project_queryset(), pk=project_id)
        phase = self.get_phase(project, phase_id)
        title = phase.title
        delete_waterfall_phase(project, phase)
        log_audit(
            project.workspace,
            request.user,
            "waterfall.phase_delete",
            "WBSNode",
            phase_id,
            summary=f"Deleted Waterfall phase {title}",
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class WBSQualityCheckListCreateView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get_node(self, wbs_id):
        return get_object_or_404(
            WBSNode.objects.filter(project__workspace=self.get_workspace()),
            pk=wbs_id,
        )

    def get(self, request, wbs_id):
        node = self.get_node(wbs_id)
        items = node.quality_checks.select_related("checked_by")
        return Response(WBSQualityCheckItemSerializer(items, many=True).data)

    def post(self, request, wbs_id):
        node = self.get_node(wbs_id)
        title = str(request.data.get("title") or "").strip()
        if not title:
            raise ValidationError({"title": "Required."})
        evidence = str(request.data.get("evidence_url") or "").strip()
        result = str(request.data.get("result") or WBSQualityCheckItem.Result.OPEN)
        if result not in WBSQualityCheckItem.Result.values:
            raise ValidationError({"result": "Invalid result."})
        position = request.data.get("position")
        if position is None:
            position = node.quality_checks.count()
        item = WBSQualityCheckItem.objects.create(
            wbs_node=node,
            title=title,
            evidence_url=evidence,
            result=result,
            position=int(position),
        )
        log_audit(
            node.project.workspace,
            request.user,
            "wbs.quality.create",
            "WBSQualityCheckItem",
            item.id,
            summary=f"Quality check on {node.code}: {title}",
        )
        return Response(
            WBSQualityCheckItemSerializer(item).data,
            status=status.HTTP_201_CREATED,
        )


class WBSQualityCheckDetailView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get_item(self, item_id):
        return get_object_or_404(
            WBSQualityCheckItem.objects.filter(
                wbs_node__project__workspace=self.get_workspace()
            ).select_related("wbs_node", "checked_by"),
            pk=item_id,
        )

    def patch(self, request, item_id):
        from django.utils import timezone

        item = self.get_item(item_id)
        if "title" in request.data:
            title = str(request.data.get("title") or "").strip()
            if not title:
                raise ValidationError({"title": "Required."})
            item.title = title
        if "evidence_url" in request.data:
            item.evidence_url = str(request.data.get("evidence_url") or "").strip()
        if "position" in request.data and request.data.get("position") is not None:
            item.position = int(request.data["position"])
        if "result" in request.data:
            result = str(request.data.get("result") or "")
            if result not in WBSQualityCheckItem.Result.values:
                raise ValidationError({"result": "Invalid result."})
            item.result = result
            if result in (
                WBSQualityCheckItem.Result.PASS,
                WBSQualityCheckItem.Result.FAIL,
            ):
                item.checked_by = request.user
                item.checked_at = timezone.now()
            elif result == WBSQualityCheckItem.Result.OPEN:
                item.checked_by = None
                item.checked_at = None
        item.save()
        return Response(WBSQualityCheckItemSerializer(item).data)

    def delete(self, request, item_id):
        item = self.get_item(item_id)
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

