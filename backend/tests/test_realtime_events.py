import pytest
from rest_framework import status

from workspaces.events import event_stream, publish_event, subscribe, unsubscribe


def test_publish_event_delivers_to_subscriber():
    workspace_id = 999001
    q = subscribe(workspace_id)
    try:
        publish_event(workspace_id, "wbs.updated", {"wbs_id": 1})
        message = q.get_nowait()
        assert message["type"] == "wbs.updated"
        assert message["payload"] == {"wbs_id": 1}
    finally:
        unsubscribe(workspace_id, q)


def test_publish_event_without_subscribers_is_noop():
    # Should not raise even though nobody is listening.
    publish_event(999002, "wbs.updated", {"wbs_id": 1})


def test_event_stream_generator_yields_published_event():
    workspace_id = 999003
    q = subscribe(workspace_id)
    try:
        publish_event(workspace_id, "comment.created", {"comment_id": 42})
        gen = event_stream(workspace_id, q)
        first_chunk = next(gen)
        assert "retry" in first_chunk
        second_chunk = next(gen)
        assert "comment.created" in second_chunk
        assert '"comment_id": 42' in second_chunk
        gen.close()
    finally:
        unsubscribe(workspace_id, q)


def test_unsubscribe_removes_from_registry():
    workspace_id = 999004
    q = subscribe(workspace_id)
    unsubscribe(workspace_id, q)
    # Publishing after unsubscribe should not error and queue stays empty.
    publish_event(workspace_id, "wbs.updated", {})
    assert q.empty()


@pytest.mark.django_db
def test_workspace_events_endpoint_returns_stream_headers(authenticated_client):
    response = authenticated_client.get("/api/workspace/events/")
    assert response.status_code == status.HTTP_200_OK
    assert response["Content-Type"].startswith("text/event-stream")
    # Do not touch response.content / streaming_content: it is an infinite
    # generator by design (SSE keeps the connection open).
    response.close()


@pytest.mark.django_db
def test_card_move_publishes_event(authenticated_client, board, column, card):
    from kanban.models import Column

    target_column = Column.objects.create(board=board, title="Done", position=1)
    q = subscribe(board.workspace_id)
    try:
        response = authenticated_client.post(
            f"/api/cards/{card.id}/move/",
            {"column_id": target_column.id, "position": 0},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        message = q.get_nowait()
        assert message["type"] == "card.moved"
        assert message["payload"]["card_id"] == card.id
    finally:
        unsubscribe(board.workspace_id, q)
