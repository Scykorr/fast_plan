from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from delivery.models import AgentProfile
from delivery.serializers import AgentProfileSerializer
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
    PackageTransferSerializer,
    PackageTransitionSerializer,
    PackageWriteSerializer,
)
from ladya.services import (
    apply_manifest_sha256,
    assert_intake_transition,
    convert_intake_to_package,
    create_delivery_task_from_package,
    sha256_of_upload,
    transfer_package,
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


def _package_max_bytes() -> int:
    return int(getattr(settings, "LADYA_PACKAGE_MAX_BYTES", 256 * 1024 * 1024))


def _validate_upload(upload):
    if not upload:
        raise ValidationError({"file": "Файл обязателен."})
    limit = _package_max_bytes()
    size = getattr(upload, "size", None)
    if size is not None and size > limit:
        raise ValidationError(
            {"file": f"Файл превышает лимит {limit} байт (LADYA_PACKAGE_MAX_BYTES)."}
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
        serializer = LaboratoryWriteSerializer(
            lab,
            data=request.data,
            partial=True,
            context={"workspace": self.get_workspace()},
        )
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
        from_lab = request.query_params.get("from_lab")
        if from_lab:
            qs = qs.filter(from_laboratory_id=from_lab)
        to_lab = request.query_params.get("to_lab")
        if to_lab:
            qs = qs.filter(to_laboratory_id=to_lab)
        q = (request.query_params.get("q") or "").strip()
        if q:
            qs = qs.filter(title__icontains=q)
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
        status_filter = request.query_params.get("status")
        if status_filter:
            rows = rows.filter(status=status_filter)
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

        to_lab = get_object_or_404(
            Laboratory, pk=data["to_laboratory"], workspace=ws, is_active=True
        )

        # Allow convert from NEW by first moving to TRIAGED implicitly if still NEW.
        if intake.status == IntakeRequest.Status.NEW:
            intake.status = IntakeRequest.Status.TRIAGED
            intake.save(update_fields=["status", "updated_at"])

        default_title = " ".join((intake.body or "").split()[:8]).strip()
        package = convert_intake_to_package(
            intake,
            user=request.user,
            title=data.get("title") or default_title or f"Intake #{intake.pk}",
            summary=data.get("summary") or "",
            from_laboratory=lab_or_none("from_laboratory"),
            to_laboratory=to_lab,
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


class PackageTransferView(WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def post(self, request, package_id):
        self.require_editor()
        ws = self.get_workspace()
        _ensure_ladya_enabled(ws)
        package = get_object_or_404(Package, pk=package_id, workspace=ws)
        serializer = PackageTransferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        to_lab = get_object_or_404(
            Laboratory,
            pk=serializer.validated_data["to_laboratory"],
            workspace=ws,
        )
        package = transfer_package(
            package,
            to_laboratory=to_lab,
            user=request.user,
            reason=serializer.validated_data.get("reason", ""),
        )
        package = Package.objects.prefetch_related("files", "status_events").get(
            pk=package.pk
        )
        return Response(PackageSerializer(package).data)


class PackageCreateDeliveryTaskView(WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def post(self, request, package_id):
        self.require_editor()
        ws = self.get_workspace()
        _ensure_ladya_enabled(ws)
        package = get_object_or_404(Package, pk=package_id, workspace=ws)
        task = create_delivery_task_from_package(package, user=request.user)
        package = Package.objects.prefetch_related("files", "status_events").get(
            pk=package.pk
        )
        return Response(
            {
                "package": PackageSerializer(package).data,
                "delivery_task": {
                    "id": task.id,
                    "title": task.title,
                    "status": task.status,
                    "assignee": task.assignee_id,
                },
            },
            status=status.HTTP_201_CREATED,
        )


class PackageManifestView(WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def post(self, request, package_id):
        self.require_editor()
        ws = self.get_workspace()
        _ensure_ladya_enabled(ws)
        package = get_object_or_404(
            Package.objects.filter(workspace=ws).prefetch_related("files"),
            pk=package_id,
        )
        manifest, digest = apply_manifest_sha256(package)
        return Response({"manifest": manifest, "manifest_sha256": digest})

    def get(self, request, package_id):
        ws = self.get_workspace()
        _ensure_ladya_enabled(ws)
        package = get_object_or_404(
            Package.objects.filter(workspace=ws).prefetch_related("files"),
            pk=package_id,
        )
        from ladya.services import build_package_manifest, canonical_manifest_json

        manifest = build_package_manifest(package)
        raw = canonical_manifest_json(manifest)
        from django.http import HttpResponse

        response = HttpResponse(raw, content_type="application/json")
        response["Content-Disposition"] = (
            f'attachment; filename="{package.display_code}-manifest.json"'
        )
        return response


class LaboratoryPackagesView(WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def get(self, request, lab_id):
        from django.db.models import Q

        ws = self.get_workspace()
        _ensure_ladya_enabled(ws)
        lab = get_object_or_404(Laboratory, pk=lab_id, workspace=ws)
        direction = request.query_params.get("direction", "all")
        status_filter = request.query_params.get("status")
        if direction == "incoming":
            packages = Package.objects.filter(workspace=ws, to_laboratory=lab)
        elif direction == "outgoing":
            packages = Package.objects.filter(workspace=ws, from_laboratory=lab)
        else:
            packages = Package.objects.filter(workspace=ws).filter(
                Q(from_laboratory=lab) | Q(to_laboratory=lab)
            )
        if status_filter:
            packages = packages.filter(status=status_filter)
        packages = packages.prefetch_related("files", "status_events").distinct()
        return Response(
            {
                "laboratory": LaboratorySerializer(lab).data,
                "packages": PackageSerializer(packages, many=True).data,
            }
        )


class LadyaEventsFeedView(WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def get(self, request):
        from ladya.models import PackageStatusEvent
        from ladya.serializers import PackageStatusEventSerializer

        ws = self.get_workspace()
        _ensure_ladya_enabled(ws)
        try:
            limit = min(int(request.query_params.get("limit", 30)), 100)
        except (TypeError, ValueError):
            limit = 30
        events = (
            PackageStatusEvent.objects.filter(package__workspace=ws)
            .select_related("package", "changed_by")
            .order_by("-created_at")[:limit]
        )
        data = []
        for event in events:
            row = PackageStatusEventSerializer(event).data
            row["package_id"] = event.package_id
            row["package_code"] = event.package.display_code
            row["package_title"] = event.package.title
            data.append(row)
        return Response(data)


class LaboratoryEnsureChatView(WorkspaceMixin, APIView):
    """Bind laboratory to workspace portfolio ChatRoom."""

    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def post(self, request, lab_id):
        self.require_editor()
        ws = self.get_workspace()
        _ensure_ladya_enabled(ws)
        from ladya.chat_bridge import ensure_laboratory_chat_room

        lab = get_object_or_404(Laboratory, pk=lab_id, workspace=ws)
        room = ensure_laboratory_chat_room(lab)
        return Response(
            {
                "laboratory": LaboratorySerializer(lab).data,
                "chat_room_id": room.id,
                "open_path": "/portfolio?chat=1",
            }
        )


class ChatRoomLadyaCapabilitiesView(WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceMember]

    def get(self, request, room_id):
        ws = self.get_workspace()
        try:
            _ensure_ladya_enabled(ws)
        except PermissionDenied:
            return Response(
                {"ladya_enabled": False, "can_create_intake": False, "lab_ids": []}
            )
        from chats.models import ChatRoom
        from ladya.chat_bridge import room_allows_intake_create

        room = get_object_or_404(ChatRoom, pk=room_id)
        if room.host_workspace_id != ws.id:
            raise PermissionDenied("Чат из другого workspace.")
        from workspaces.models import WorkspaceMember

        labs = list(
            Laboratory.objects.filter(workspace=ws, chat_room_id=room_id).values_list(
                "id", flat=True
            )
        )
        membership = WorkspaceMember.objects.filter(
            workspace=ws, user=request.user
        ).first()
        is_editor = bool(
            membership
            and membership.role
            in (WorkspaceMember.Role.OWNER, WorkspaceMember.Role.EDITOR)
        )
        can = is_editor and room_allows_intake_create(ws, room)
        return Response(
            {
                "ladya_enabled": True,
                "can_create_intake": can,
                "lab_ids": labs,
            }
        )


class IntakeFromChatMessageView(WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def post(self, request):
        self.require_editor()
        ws = self.get_workspace()
        _ensure_ladya_enabled(ws)
        from chats.models import ChatMessage
        from ladya.chat_bridge import create_intake_from_chat_message

        message_id = request.data.get("message_id")
        if not message_id:
            raise ValidationError({"message_id": "Required"})
        message = get_object_or_404(
            ChatMessage.objects.select_related("room", "author"), pk=message_id
        )
        try:
            intake = create_intake_from_chat_message(
                workspace=ws, message=message, actor=request.user
            )
        except ValueError as exc:
            raise ValidationError({"detail": str(exc)}) from exc
        return Response(
            IntakeRequestSerializer(intake).data, status=status.HTTP_201_CREATED
        )


class PackageNotifyChatView(WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def post(self, request, package_id):
        self.require_editor()
        ws = self.get_workspace()
        _ensure_ladya_enabled(ws)
        from ladya.chat_bridge import post_package_notice

        package = get_object_or_404(
            Package.objects.select_related("to_laboratory", "to_laboratory__chat_room"),
            pk=package_id,
            workspace=ws,
        )
        try:
            msg = post_package_notice(
                package=package,
                actor=request.user,
                text=request.data.get("text") or None,
            )
        except ValueError as exc:
            raise ValidationError({"detail": str(exc)}) from exc
        return Response(
            {"message_id": msg.id, "room_id": msg.room_id, "body": msg.body},
            status=status.HTTP_201_CREATED,
        )


class LaboratoryAgentsView(WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def get(self, request, lab_id):
        ws = self.get_workspace()
        _ensure_ladya_enabled(ws)
        lab = get_object_or_404(Laboratory, pk=lab_id, workspace=ws)
        rows = lab.agents.filter(workspace=ws).select_related("user", "api_token")
        return Response(AgentProfileSerializer(rows, many=True).data)


class LadyaAgentConnectView(WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def get(self, request):
        ws = self.get_workspace()
        _ensure_ladya_enabled(ws)
        lab_id = request.query_params.get("laboratory")
        qs = AgentProfile.objects.filter(workspace=ws).select_related("user")
        if lab_id:
            lab = get_object_or_404(Laboratory, pk=lab_id, workspace=ws)
            qs = lab.agents.all()
        else:
            qs = qs.filter(ladya_role__gt="").distinct()
        return Response(AgentProfileSerializer(qs, many=True).data)

    def post(self, request):
        self.require_editor()
        ws = self.get_workspace()
        _ensure_ladya_enabled(ws)
        from ladya.agent_connect import build_connect_instruction, connect_agent

        ladya_role = (request.data.get("ladya_role") or "").strip()
        display_name = (request.data.get("display_name") or "").strip()
        ops_role = (request.data.get("ops_role") or "").strip() or None
        lab = None
        lab_id = request.data.get("laboratory")
        if lab_id not in (None, ""):
            lab = get_object_or_404(Laboratory, pk=lab_id, workspace=ws)
        try:
            profile, raw, email = connect_agent(
                workspace=ws,
                actor=request.user,
                ladya_role=ladya_role,
                display_name=display_name,
                laboratory=lab,
                ops_role=ops_role,
            )
        except ValueError as exc:
            raise ValidationError({"detail": str(exc)}) from exc
        base = request.build_absolute_uri("/").rstrip("/")
        # Prefer frontend origin hint if provided
        fe = (request.data.get("frontend_base_url") or "").strip().rstrip("/")
        api_base = fe or base
        instruction = build_connect_instruction(
            profile=profile,
            workspace_id=ws.id,
            base_url=api_base,
            token=raw,
            laboratory=lab,
        )
        data = AgentProfileSerializer(profile).data
        data["api_token_raw"] = raw
        data["service_user_email"] = email
        data["workspace_id"] = ws.id
        data["connect_instruction"] = instruction
        data["laboratory_id"] = lab.id if lab else None
        return Response(data, status=status.HTTP_201_CREATED)


class LadyaAgentReissueView(WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def post(self, request, agent_id):
        self.require_editor()
        ws = self.get_workspace()
        _ensure_ladya_enabled(ws)
        from ladya.agent_connect import build_connect_instruction, reissue_agent_token

        profile = get_object_or_404(
            AgentProfile.objects.select_related("user"), pk=agent_id, workspace=ws
        )
        lab = profile.ladya_laboratories.filter(workspace=ws).first()
        try:
            raw = reissue_agent_token(
                workspace=ws, actor=request.user, profile=profile
            )
        except ValueError as exc:
            raise ValidationError({"detail": str(exc)}) from exc
        base = (request.data.get("frontend_base_url") or "").strip().rstrip("/")
        if not base:
            base = request.build_absolute_uri("/").rstrip("/")
        instruction = build_connect_instruction(
            profile=profile,
            workspace_id=ws.id,
            base_url=base,
            token=raw,
            laboratory=lab,
        )
        data = AgentProfileSerializer(profile).data
        data["api_token_raw"] = raw
        data["connect_instruction"] = instruction
        data["workspace_id"] = ws.id
        return Response(data)


class LadyaAgentRevokeView(WorkspaceMixin, APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceEditorOrReadOnly]

    def post(self, request, agent_id):
        self.require_editor()
        ws = self.get_workspace()
        _ensure_ladya_enabled(ws)
        from ladya.agent_connect import revoke_agent_token

        profile = get_object_or_404(AgentProfile, pk=agent_id, workspace=ws)
        try:
            revoke_agent_token(workspace=ws, actor=request.user, profile=profile)
        except ValueError as exc:
            raise ValidationError({"detail": str(exc)}) from exc
        return Response(AgentProfileSerializer(profile).data)
