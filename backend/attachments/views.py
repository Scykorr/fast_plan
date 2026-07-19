from django.conf import settings
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from attachments.models import WorkItemAttachment
from attachments.serializers import WorkItemAttachmentSerializer
from kanban.models import Card
from projects.models import WBSNode
from workspaces.mixins import IsWorkspaceEditorOrReadOnly, WorkspaceMixin
from workspaces.models import WorkspaceMember
from workspaces.services import has_min_role


def _validate_upload(upload):
    if not upload:
        raise ValidationError({"file": "File is required."})
    if upload.size > settings.ATTACHMENT_MAX_BYTES:
        raise ValidationError(
            {
                "file": (
                    f"File exceeds the {settings.ATTACHMENT_MAX_BYTES} bytes limit."
                )
            }
        )


class WBSAttachmentListCreateView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]
    parser_classes = [MultiPartParser, FormParser]

    def get_node(self, wbs_id):
        return get_object_or_404(
            WBSNode.objects.filter(project__workspace=self.get_workspace()),
            pk=wbs_id,
        )

    def get(self, request, wbs_id):
        node = self.get_node(wbs_id)
        attachments = node.attachments.select_related("uploaded_by")
        return Response(WorkItemAttachmentSerializer(attachments, many=True).data)

    def post(self, request, wbs_id):
        node = self.get_node(wbs_id)
        upload = request.data.get("file")
        _validate_upload(upload)
        attachment = WorkItemAttachment.objects.create(
            wbs_node=node,
            file=upload,
            uploaded_by=request.user,
            name=upload.name,
            size=upload.size,
            content_type=getattr(upload, "content_type", "") or "",
        )
        return Response(
            WorkItemAttachmentSerializer(attachment).data,
            status=status.HTTP_201_CREATED,
        )


class CardAttachmentListCreateView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]
    parser_classes = [MultiPartParser, FormParser]

    def get_card(self, card_id):
        return get_object_or_404(
            Card.objects.filter(column__board__workspace=self.get_workspace()),
            pk=card_id,
        )

    def get(self, request, card_id):
        card = self.get_card(card_id)
        attachments = card.attachments.select_related("uploaded_by")
        return Response(WorkItemAttachmentSerializer(attachments, many=True).data)

    def post(self, request, card_id):
        card = self.get_card(card_id)
        upload = request.data.get("file")
        _validate_upload(upload)
        attachment = WorkItemAttachment.objects.create(
            card=card,
            file=upload,
            uploaded_by=request.user,
            name=upload.name,
            size=upload.size,
            content_type=getattr(upload, "content_type", "") or "",
        )
        return Response(
            WorkItemAttachmentSerializer(attachment).data,
            status=status.HTTP_201_CREATED,
        )


class AttachmentDetailView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get_attachment(self, attachment_id):
        workspace = self.get_workspace()
        return get_object_or_404(
            WorkItemAttachment.objects.filter(
                Q(wbs_node__project__workspace=workspace)
                | Q(card__column__board__workspace=workspace)
            ),
            pk=attachment_id,
        )

    def delete(self, request, attachment_id):
        attachment = self.get_attachment(attachment_id)
        workspace = self.get_workspace()
        if attachment.uploaded_by_id != request.user.id and not has_min_role(
            workspace, request.user, WorkspaceMember.Role.OWNER
        ):
            raise ValidationError("Only the uploader or workspace owner can delete.")
        attachment.file.delete(save=False)
        attachment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
