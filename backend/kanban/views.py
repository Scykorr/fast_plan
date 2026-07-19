from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from kanban.models import Board, Card, CardTransition, Column
from kanban.analytics import build_board_flow_analytics
from kanban.serializers import (
    BoardDetailSerializer,
    BoardListSerializer,
    BoardWriteSerializer,
    CardMoveSerializer,
    CardSerializer,
    CardWriteSerializer,
    ColumnSerializer,
    ColumnWriteSerializer,
)
from kanban.services import move_card, move_column, reorder_column_positions, reorder_positions
from projects.sync import sync_activity_from_card
from workspaces.events import publish_event
from workspaces.mixins import IsWorkspaceEditorOrReadOnly, WorkspaceMixin


class BoardWorkspaceMixin(WorkspaceMixin):
    def get_board_queryset(self):
        return Board.objects.filter(workspace=self.get_workspace())

    def get_column_queryset(self):
        return Column.objects.filter(board__workspace=self.get_workspace())

    def get_card_queryset(self):
        return Card.objects.filter(column__board__workspace=self.get_workspace())


class BoardListCreateView(BoardWorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]
    def get(self, request):
        boards = self.get_board_queryset()
        return Response(BoardListSerializer(boards, many=True).data)

    def post(self, request):
        serializer = BoardWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        board = Board.objects.create(
            workspace=self.get_workspace(),
            **serializer.validated_data,
        )
        return Response(
            BoardDetailSerializer(board).data,
            status=status.HTTP_201_CREATED,
        )


class BoardDetailView(BoardWorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get_board(self, board_id):
        return get_object_or_404(self.get_board_queryset(), pk=board_id)

    def get(self, request, board_id):
        board = self.get_board(board_id)
        return Response(BoardDetailSerializer(board).data)

    def patch(self, request, board_id):
        board = self.get_board(board_id)
        serializer = BoardWriteSerializer(board, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(BoardDetailSerializer(board).data)

    def delete(self, request, board_id):
        board = self.get_board(board_id)
        board.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class BoardAnalyticsView(BoardWorkspaceMixin, APIView):
    def get(self, request, board_id):
        board = get_object_or_404(self.get_board_queryset(), pk=board_id)
        return Response(
            build_board_flow_analytics(
                board,
                days=request.query_params.get("days", 14),
            )
        )


class ColumnListCreateView(BoardWorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def post(self, request, board_id):
        board = get_object_or_404(self.get_board_queryset(), pk=board_id)
        serializer = ColumnWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        column = Column.objects.create(
            board=board,
            title=data.get("title", "Новая колонка"),
            position=data.get("position", board.columns.count()),
        )
        return Response(ColumnSerializer(column).data, status=status.HTTP_201_CREATED)


class ColumnDetailView(BoardWorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get_column(self, column_id):
        return get_object_or_404(self.get_column_queryset(), pk=column_id)

    def patch(self, request, column_id):
        column = self.get_column(column_id)
        serializer = ColumnWriteSerializer(column, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if "title" in data:
            column.title = data["title"]
            column.save(update_fields=["title"])

        if "position" in data:
            column = move_column(column, data["position"])

        return Response(ColumnSerializer(column).data)

    def delete(self, request, column_id):
        column = self.get_column(column_id)
        board = column.board
        column.delete()
        reorder_column_positions(board.columns.all())
        return Response(status=status.HTTP_204_NO_CONTENT)


class CardListCreateView(BoardWorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def post(self, request, column_id):
        column = get_object_or_404(self.get_column_queryset(), pk=column_id)
        serializer = CardWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        position = serializer.validated_data.get("position", column.cards.count())
        card = Card.objects.create(
            column=column,
            position=position,
            title=serializer.validated_data.get("title", "Новая карточка"),
            description=serializer.validated_data.get("description", ""),
            due_date=serializer.validated_data.get("due_date"),
        )
        return Response(CardSerializer(card).data, status=status.HTTP_201_CREATED)


class CardDetailView(BoardWorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def get_card(self, card_id):
        return get_object_or_404(self.get_card_queryset(), pk=card_id)

    def patch(self, request, card_id):
        card = self.get_card(card_id)
        serializer = CardWriteSerializer(card, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(CardSerializer(card).data)

    def delete(self, request, card_id):
        card = self.get_card(card_id)
        card.delete()
        reorder_positions(card.column.cards.all())
        return Response(status=status.HTTP_204_NO_CONTENT)


class CardMoveView(BoardWorkspaceMixin, APIView):
    permission_classes = [IsWorkspaceEditorOrReadOnly]

    def post(self, request, card_id):
        card = get_object_or_404(self.get_card_queryset(), pk=card_id)
        serializer = CardMoveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        target_column = get_object_or_404(
            self.get_column_queryset(),
            pk=serializer.validated_data["column_id"],
        )
        if target_column.board_id != card.column.board_id:
            raise PermissionDenied("Card can only move within the same board.")

        previous_column = card.column
        card = move_card(
            card,
            target_column,
            serializer.validated_data["position"],
        )
        if previous_column.id != target_column.id:
            CardTransition.objects.create(
                card=card,
                from_column=previous_column,
                to_column=target_column,
                moved_by=request.user,
            )
        sync_activity_from_card(card)
        publish_event(
            self.get_workspace().id,
            "card.moved",
            {
                "card_id": card.id,
                "column_id": card.column_id,
                "board_id": target_column.board_id,
            },
        )
        return Response(CardSerializer(card).data)
