"""P4 API views: share links, PERT, AI drafts, project members, CSV import."""

import secrets

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.services import log_audit
from projects.ai import draft_project_content
from projects.imports import import_jira_csv, import_wbs_csv
from projects.models import Project, ProjectMember, ProjectShareLink
from projects.pert import compute_pert_network
from projects.reports import build_status_report
from projects.views import WorkspaceMixin
from workspaces.mixins import IsWorkspaceEditorOrReadOnly


class ProjectImportView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, project_id):
        project = get_object_or_404(self.get_project_queryset(), pk=project_id)
        upload = request.FILES.get("file")
        if upload is None:
            raise ValidationError({"file": "CSV file is required."})
        import_format = str(request.data.get("format", "wbs")).strip().lower()
        try:
            raw = upload.read()
            if import_format == "jira":
                result = import_jira_csv(project, raw)
            elif import_format in ("wbs", ""):
                result = import_wbs_csv(project, raw)
            else:
                raise ValidationError({"format": "Supported formats: wbs, jira."})
        except ValueError as exc:
            raise ValidationError({"file": str(exc)}) from exc
        log_audit(
            project.workspace,
            request.user,
            "wbs.import",
            "Project",
            project.id,
            summary=(
                f"Imported {result.get('format', 'wbs')} CSV "
                f"({result['created']} created, {result['updated']} updated)"
            ),
            changes=result,
        )
        return Response(result)


class ProjectPertView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get(self, request, project_id):
        project = get_object_or_404(self.get_project_queryset(), pk=project_id)
        return Response(compute_pert_network(project))


class ProjectAIDraftView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def post(self, request, project_id):
        project = get_object_or_404(self.get_project_queryset(), pk=project_id)
        target = str(request.data.get("target", "")).strip()
        prompt = str(request.data.get("prompt", "")).strip()
        try:
            draft = draft_project_content(project, target=target, prompt=prompt)
        except ValueError as exc:
            raise ValidationError({"target": str(exc)}) from exc
        return Response(draft)


class ProjectShareLinkListCreateView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get(self, request, project_id):
        project = get_object_or_404(self.get_project_queryset(), pk=project_id)
        links = project.share_links.filter(revoked_at__isnull=True)
        return Response(
            [
                {
                    "id": link.id,
                    "token": link.token,
                    "label": link.label,
                    "created_at": link.created_at,
                    "expires_at": link.expires_at,
                    "last_accessed_at": link.last_accessed_at,
                    "is_active": link.is_active,
                }
                for link in links
            ]
        )

    def post(self, request, project_id):
        project = get_object_or_404(self.get_project_queryset(), pk=project_id)
        expires_raw = request.data.get("expires_at")
        expires_at = None
        if expires_raw:
            expires_at = timezone.datetime.fromisoformat(str(expires_raw).replace("Z", "+00:00"))
            if timezone.is_naive(expires_at):
                expires_at = timezone.make_aware(expires_at)
        link = ProjectShareLink.objects.create(
            project=project,
            token=secrets.token_urlsafe(24),
            label=str(request.data.get("label", "")).strip()[:100],
            created_by=request.user,
            expires_at=expires_at,
        )
        log_audit(
            project.workspace,
            request.user,
            "share_link.create",
            "ProjectShareLink",
            link.id,
            summary=f"Created guest status-report link for {project.name}",
        )
        return Response(
            {
                "id": link.id,
                "token": link.token,
                "label": link.label,
                "created_at": link.created_at,
                "expires_at": link.expires_at,
                "is_active": True,
                "url_path": f"/share/{link.token}",
            },
            status=status.HTTP_201_CREATED,
        )


class ProjectShareLinkDetailView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def delete(self, request, project_id, link_id):
        project = get_object_or_404(self.get_project_queryset(), pk=project_id)
        link = get_object_or_404(project.share_links, pk=link_id)
        link.revoked_at = timezone.now()
        link.save(update_fields=["revoked_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class PublicStatusReportView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, token):
        link = (
            ProjectShareLink.objects.select_related("project", "project__workspace")
            .filter(token=token)
            .first()
        )
        if link is None or not link.is_active:
            raise NotFound("Share link not found or expired.")
        link.last_accessed_at = timezone.now()
        link.save(update_fields=["last_accessed_at"])
        report = build_status_report(link.project)
        report["share"] = {
            "label": link.label,
            "project_name": link.project.name,
            "workspace_name": link.project.workspace.name,
        }
        return Response(report)


class ProjectMemberListCreateView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get(self, request, project_id):
        project = get_object_or_404(self.get_project_queryset(), pk=project_id)
        members = project.memberships.select_related("user")
        return Response(
            [
                {
                    "id": member.id,
                    "user_id": member.user_id,
                    "email": member.user.email,
                    "username": member.user.username,
                    "role": member.role,
                    "created_at": member.created_at,
                }
                for member in members
            ]
        )

    def post(self, request, project_id):
        project = get_object_or_404(self.get_project_queryset(), pk=project_id)
        user_id = request.data.get("user_id")
        role = request.data.get("role", ProjectMember.Role.CONTRIBUTOR)
        if role not in ProjectMember.Role.values:
            raise ValidationError({"role": "Invalid project role."})
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = get_object_or_404(
            User.objects.filter(workspace_memberships__workspace=project.workspace),
            pk=user_id,
        )
        member, created = ProjectMember.objects.update_or_create(
            project=project,
            user=user,
            defaults={"role": role},
        )
        return Response(
            {
                "id": member.id,
                "user_id": member.user_id,
                "email": member.user.email,
                "username": member.user.username,
                "role": member.role,
                "created_at": member.created_at,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class ProjectMemberDetailView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def delete(self, request, project_id, member_id):
        project = get_object_or_404(self.get_project_queryset(), pk=project_id)
        member = get_object_or_404(project.memberships, pk=member_id)
        member.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
