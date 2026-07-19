from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from kanban.models import Card
from notifications.services import notify_new_comment
from projects.models import WBSNode, WorkItemComment
from projects.serializers_comments import (
    WorkItemCommentSerializer,
    WorkItemCommentWriteSerializer,
)
from projects.views import WorkspaceMixin
from workspaces.mixins import IsWorkspaceEditorOrReadOnly
from workspaces.models import WorkspaceMember
from workspaces.services import get_membership, has_min_role


class WBSCommentListCreateView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get_node(self, wbs_id):
        return get_object_or_404(self.get_wbs_queryset(), pk=wbs_id)

    def get(self, request, wbs_id):
        node = self.get_node(wbs_id)
        comments = node.comments.select_related("author").all()
        return Response(WorkItemCommentSerializer(comments, many=True).data)

    def post(self, request, wbs_id):
        node = self.get_node(wbs_id)
        serializer = WorkItemCommentWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment = WorkItemComment.objects.create(
            workspace=node.project.workspace,
            author=request.user,
            wbs_node=node,
            kind=serializer.validated_data["kind"],
            body=serializer.validated_data["body"].strip(),
        )
        notify_new_comment(comment)
        return Response(
            WorkItemCommentSerializer(comment).data,
            status=status.HTTP_201_CREATED,
        )


class CardCommentListCreateView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get_card(self, card_id):
        return get_object_or_404(
            Card.objects.filter(column__board__workspace=self.get_workspace()),
            pk=card_id,
        )

    def get(self, request, card_id):
        card = self.get_card(card_id)
        comments = card.comments.select_related("author").all()
        return Response(WorkItemCommentSerializer(comments, many=True).data)

    def post(self, request, card_id):
        card = self.get_card(card_id)
        serializer = WorkItemCommentWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment = WorkItemComment.objects.create(
            workspace=card.column.board.workspace,
            author=request.user,
            card=card,
            kind=serializer.validated_data["kind"],
            body=serializer.validated_data["body"].strip(),
        )
        notify_new_comment(comment)
        return Response(
            WorkItemCommentSerializer(comment).data,
            status=status.HTTP_201_CREATED,
        )


class WorkItemCommentDetailView(WorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get_comment(self, comment_id):
        return get_object_or_404(
            WorkItemComment.objects.filter(workspace=self.get_workspace()),
            pk=comment_id,
        )

    def delete(self, request, comment_id):
        comment = self.get_comment(comment_id)
        workspace = self.get_workspace()
        if comment.author_id != request.user.id and not has_min_role(
            workspace, request.user, WorkspaceMember.Role.OWNER
        ):
            raise ValidationError("Only the author or workspace owner can delete.")
        comment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
