from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ladya.defaults import get_or_create_ladya_settings
from ladya.models import IntakeRequest, Laboratory, Package, PackageFile
from ladya.serializers import (
    IntakeConvertSerializer,
    IntakeRequestSerializer,
    IntakeTriageSerializer,
    IntakeWriteSerializer,
    LaboratorySerializer,
    LaboratoryWriteSerializer,
    LadyaSettingsSerializer,
    PackageFileSerializer,
    PackageSerializer,
    PackageTransitionSerializer,
    PackageWriteSerializer,
)
from ladya.services import (
    assert_intake_transition,
    convert_intake_to_package,
    sha256_of_upload,
    transition_package,
)
from workspaces.mixins import (
    IsWorkspaceEditorOrReadOnly,
    IsWorkspaceMember,
    WorkspaceMixin,
)


def _ensure_ladya_enabled(workspace):
    row, _ = get_or_create_ladya_settings(workspace)
    if not row.ladya_hub_enabled:
        raise PermissionDenied("Ladya Hub выключен для этого workspace.")
    return row


def _validate_upload(upload):
    if not upload:
        raise ValidationError({"file": "Файл обязателен."})
    if upload.size > settings.ATTACHMENT_MAX_BYTES:
        raise ValidationError(
            {
                "file": (
                    f"Файл превышает лимит {settings.ATTACHMENT_MAX_BYTES} байт."
                )
            }
        )


class LadyaSettingsView(WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def get(self, request):
        row, _ = get_or_create_ladya_settings(self.get_workspace())
        return Response(LadyaSettingsSerializer(row).data)

    def patch(self, request):
        self.require_editor()
        row, _ = get_or_create_ladya_settings(self.get_workspace())
        if "ladya_hub_enabled" in request.data:
            row.ladya_hub_enabled = bool(request.data.get("ladya_hub_enabled"))
        row.save()
        return Response(LadyaSettingsSerializer(row).data)


class LaboratoryListCreateView(WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def get(self, request):
        ws = self.get_workspace()
        _ensure_ladya_enabled(ws)
        labs = Laboratory.objects.filter(workspace=ws)
        return Response(LaboratorySerializer(labs, many=True).data)

    def post(self, request):
        self.require_editor()
        ws = self.get_workspace()
        _ensure_ladya_enabled(ws)
        serializer = LaboratoryWriteSerializer(
            data=request.data, context={"workspace": ws}
        )
        serializer.is_valid(raise_exception=True)
        lab = serializer.save()
        return Response(
            LaboratorySerializer(lab).data, status=status.HTTP_201_CREATED
        )


class LaboratoryDetailView(WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def get_lab(self, lab_id):
        ws = self.get_workspace()
        _ensure_ladya_enabled(ws)
        return get_object_or_404(Laboratory, pk=lab_id, workspace=ws)

    def get(self, request, lab_id):
        return Response(LaboratorySerializer(self.get_lab(lab_id)).data)

    def patch(self, request, lab_id):
        self.require_editor()
        lab = self.get_lab(lab_id)
        serializer = LaboratoryWriteSerializer(lab, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        lab = serializer.save()
        return Response(LaboratorySerializer(lab).data)

    def delete(self, request, lab_id):
        self.require_editor()
        lab = self.get_lab(lab_id)
        lab.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PackageListCreateView(WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def get_queryset(self):
        ws = self.get_workspace()
        _ensure_ladya_enabled(ws)
        return Package.objects.filter(workspace=ws).prefetch_related(
            "files", "status_events"
        )

    def get(self, request):
        qs = self.get_queryset()
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return Response(PackageSerializer(qs, many=True).data)

    def post(self, request):
        self.require_editor()
        ws = self.get_workspace()
        _ensure_ladya_enabled(ws)
        serializer = PackageWriteSerializer(
            data=request.data,
            context={"workspace": ws, "user": request.user},
        )
        serializer.is_valid(raise_exception=True)
        package = serializer.save()
        package = Package.objects.prefetch_related("files", "status_events").get(
            pk=package.pk
        )
        return Response(
            PackageSerializer(package).data, status=status.HTTP_201_CREATED
        )


class PackageDetailView(WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def get_package(self, package_id):
        ws = self.get_workspace()
        _ensure_ladya_enabled(ws)
        return get_object_or_404(
            Package.objects.filter(workspace=ws).prefetch_related(
                "files", "status_events"
            ),
            pk=package_id,
        )

    def get(self, request, package_id):
        return Response(PackageSerializer(self.get_package(package_id)).data)

    def patch(self, request, package_id):
        self.require_editor()
        package = self.get_package(package_id)
        serializer = PackageWriteSerializer(
            package,
            data=request.data,
            partial=True,
            context={"workspace": self.get_workspace(), "user": request.user},
        )
        serializer.is_valid(raise_exception=True)
        package = serializer.save()
        package = Package.objects.prefetch_related("files", "status_events").get(
            pk=package.pk
        )
        return Response(PackageSerializer(package).data)


class PackageTransitionView(WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def post(self, request, package_id):
        self.require_editor()
        ws = self.get_workspace()
        _ensure_ladya_enabled(ws)
        package = get_object_or_404(Package, pk=package_id, workspace=ws)
        serializer = PackageTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        to_lab = None
        if "to_laboratory" in serializer.validated_data:
            lab_id = serializer.validated_data["to_laboratory"]
            if lab_id is not None:
                to_lab = get_object_or_404(Laboratory, pk=lab_id, workspace=ws)
        package = transition_package(
            package,
            to_status=serializer.validated_data["status"],
            user=request.user,
            reason=serializer.validated_data.get("reason", ""),
            to_laboratory=to_lab,
        )
        package = Package.objects.prefetch_related("files", "status_events").get(
            pk=package.pk
        )
        return Response(PackageSerializer(package).data)


class PackageFileUploadView(WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, package_id):
        self.require_editor()
        ws = self.get_workspace()
        _ensure_ladya_enabled(ws)
        package = get_object_or_404(Package, pk=package_id, workspace=ws)
        upload = request.data.get("file")
        _validate_upload(upload)
        digest = sha256_of_upload(upload)
        pf = PackageFile.objects.create(
            package=package,
            file=upload,
            original_name=getattr(upload, "name", "file") or "file",
            size=getattr(upload, "size", 0) or 0,
            sha256=digest,
            content_type=getattr(upload, "content_type", "") or "",
            uploaded_by=request.user,
        )
        return Response(
            PackageFileSerializer(pf).data, status=status.HTTP_201_CREATED
        )


class IntakeListCreateView(WorkspaceMixin, APIView):
    # Members (including viewers) may submit intake; editors triage/convert.
    permission_classes = [IsAuthenticated, IsWorkspaceMember]

    def get(self, request):
        ws = self.get_workspace()
        _ensure_ladya_enabled(ws)
        rows = IntakeRequest.objects.filter(workspace=ws)
        return Response(IntakeRequestSerializer(rows, many=True).data)

    def post(self, request):
        ws = self.get_workspace()
        _ensure_ladya_enabled(ws)
        serializer = IntakeWriteSerializer(
            data=request.data,
            context={"workspace": ws, "user": request.user},
        )
        serializer.is_valid(raise_exception=True)
        intake = serializer.save()
        return Response(
            IntakeRequestSerializer(intake).data, status=status.HTTP_201_CREATED
        )


class IntakeTriageView(WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def post(self, request, intake_id):
        self.require_editor()
        ws = self.get_workspace()
        _ensure_ladya_enabled(ws)
        intake = get_object_or_404(IntakeRequest, pk=intake_id, workspace=ws)
        serializer = IntakeTriageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target = serializer.validated_data["status"]
        assert_intake_transition(intake.status, target)
        intake.status = target
        intake.save(update_fields=["status", "updated_at"])
        return Response(IntakeRequestSerializer(intake).data)


class IntakeConvertView(WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def post(self, request, intake_id):
        self.require_editor()
        ws = self.get_workspace()
        _ensure_ladya_enabled(ws)
        intake = get_object_or_404(IntakeRequest, pk=intake_id, workspace=ws)
        serializer = IntakeConvertSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        def lab_or_none(key):
            lab_id = data.get(key)
            if lab_id is None:
                return None
            return get_object_or_404(Laboratory, pk=lab_id, workspace=ws)

        # Allow convert from NEW by first moving to TRIAGED implicitly if still NEW.
        if intake.status == IntakeRequest.Status.NEW:
            intake.status = IntakeRequest.Status.TRIAGED
            intake.save(update_fields=["status", "updated_at"])

        package = convert_intake_to_package(
            intake,
            user=request.user,
            title=data.get("title") or "",
            summary=data.get("summary") or "",
            from_laboratory=lab_or_none("from_laboratory"),
            to_laboratory=lab_or_none("to_laboratory"),
        )
        package = Package.objects.prefetch_related("files", "status_events").get(
            pk=package.pk
        )
        return Response(
            {
                "intake": IntakeRequestSerializer(intake).data,
                "package": PackageSerializer(package).data,
            },
            status=status.HTTP_201_CREATED,
        )
