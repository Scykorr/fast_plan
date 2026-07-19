"""In-process pub/sub for workspace realtime events (Server-Sent Events).

Limitation: subscribers are held in a module-level dict of queues, which only
works within a single Python process. Behind multiple gunicorn/uvicorn
workers or multiple containers, events published in one process are not
visible to subscribers connected to another process. For a multi-process
deployment, replace this with Redis pub/sub (``redis-py`` is already a
dependency) or a proper channel layer.
"""

import json
import queue
import threading
import time

_lock = threading.Lock()
_subscribers: dict[int, list["queue.Queue"]] = {}

HEARTBEAT_SECONDS = 25


def subscribe(workspace_id: int) -> "queue.Queue":
    q: "queue.Queue" = queue.Queue(maxsize=200)
    with _lock:
        _subscribers.setdefault(workspace_id, []).append(q)
    return q


def unsubscribe(workspace_id: int, q: "queue.Queue") -> None:
    with _lock:
        subscribers = _subscribers.get(workspace_id)
        if not subscribers:
            return
        if q in subscribers:
            subscribers.remove(q)
        if not subscribers:
            _subscribers.pop(workspace_id, None)


def publish_event(workspace_id: int, event_type: str, payload: dict) -> None:
    """Push an event to every subscriber currently listening on a workspace."""
    with _lock:
        subscribers = list(_subscribers.get(workspace_id, []))
    if not subscribers:
        return
    message = {"type": event_type, "payload": payload, "ts": time.time()}
    for q in subscribers:
        try:
            q.put_nowait(message)
        except queue.Full:
            pass


def event_stream(workspace_id: int, q: "queue.Queue", *, heartbeat_seconds: int = HEARTBEAT_SECONDS):
    """Generator yielding SSE-formatted text for a subscriber queue."""
    yield "retry: 3000\n\n"
    while True:
        try:
            message = q.get(timeout=heartbeat_seconds)
        except queue.Empty:
            yield ": heartbeat\n\n"
            continue
        yield f"event: {message['type']}\ndata: {json.dumps(message['payload'])}\n\n"
