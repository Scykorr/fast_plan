from django.urls import path

from kanban.views import (
    BoardDetailView,
    BoardListCreateView,
    CardDetailView,
    CardListCreateView,
    CardMoveView,
    ColumnDetailView,
    ColumnListCreateView,
)

urlpatterns = [
    path("boards/", BoardListCreateView.as_view(), name="board-list"),
    path("boards/<int:board_id>/", BoardDetailView.as_view(), name="board-detail"),
    path(
        "boards/<int:board_id>/columns/",
        ColumnListCreateView.as_view(),
        name="column-list",
    ),
    path("columns/<int:column_id>/", ColumnDetailView.as_view(), name="column-detail"),
    path(
        "columns/<int:column_id>/cards/",
        CardListCreateView.as_view(),
        name="card-list",
    ),
    path("cards/<int:card_id>/", CardDetailView.as_view(), name="card-detail"),
    path("cards/<int:card_id>/move/", CardMoveView.as_view(), name="card-move"),
]
