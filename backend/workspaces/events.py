"""Workspace realtime events via Redis pub/sub (with in-process fallback).

When ``REDIS_URL`` is set, ``publish_event`` publishes to Redis and each
worker that has local SSE subscribers listens on the matching channel.
Without Redis (local tests / LocMem), behaviour falls back to the original
in-process queue fan-out so unit tests keep working.
"""

from __future__ import annotations

import json
import logging
import os
import queue
import threading
import time

logger = logging.getLogger("fast_plan")

_lock = threading.Lock()
_subscribers: dict[int, list[queue.Queue]] = {}
_redis_listeners: dict[int, threading.Thread] = {}
_redis_client = None
_redis_checked = False

HEARTBEAT_SECONDS = 25
CHANNEL_PREFIX = "fast_plan:workspace:"


def _get_redis():
    global _redis_client, _redis_checked
    if _redis_checked:
        return _redis_client
    _redis_checked = True
    url = os.environ.get("REDIS_URL", "").strip()
    if not url:
        _redis_client = None
        return None
    try:
        import redis

        client = redis.Redis.from_url(url, decode_responses=True)
        client.ping()
        _redis_client = client
    except Exception as exc:  # noqa: BLE001
        logger.warning("Redis unavailable for SSE pub/sub: %s", exc)
        _redis_client = None
    return _redis_client


def _channel_name(workspace_id: int) -> str:
    return f"{CHANNEL_PREFIX}{workspace_id}:events"


def _local_publish(workspace_id: int, message: dict) -> None:
    with _lock:
        subscribers = list(_subscribers.get(workspace_id, []))
    for q in subscribers:
        try:
            q.put_nowait(message)
        except queue.Full:
            pass


def _redis_listener_loop(workspace_id: int) -> None:
    client = _get_redis()
    if client is None:
        return
    pubsub = client.pubsub(ignore_subscribe_messages=True)
    channel = _channel_name(workspace_id)
    try:
        pubsub.subscribe(channel)
        for item in pubsub.listen():
            with _lock:
                still_needed = bool(_subscribers.get(workspace_id))
            if not still_needed:
                break
            if item.get("type") != "message":
                continue
            raw = item.get("data")
            try:
                message = json.loads(raw)
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
            _local_publish(workspace_id, message)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Redis SSE listener stopped for workspace %s: %s", workspace_id, exc)
    finally:
        try:
            pubsub.close()
        except Exception:  # noqa: BLE001
            pass
        with _lock:
            _redis_listeners.pop(workspace_id, None)


def _ensure_redis_listener(workspace_id: int) -> None:
    if _get_redis() is None:
        return
    with _lock:
        thread = _redis_listeners.get(workspace_id)
        if thread is not None and thread.is_alive():
            return
        thread = threading.Thread(
            target=_redis_listener_loop,
            args=(workspace_id,),
            name=f"sse-redis-{workspace_id}",
            daemon=True,
        )
        _redis_listeners[workspace_id] = thread
        thread.start()


def subscribe(workspace_id: int) -> queue.Queue:
    q: queue.Queue = queue.Queue(maxsize=200)
    with _lock:
        _subscribers.setdefault(workspace_id, []).append(q)
    _ensure_redis_listener(workspace_id)
    return q


def unsubscribe(workspace_id: int, q: queue.Queue) -> None:
    with _lock:
        subscribers = _subscribers.get(workspace_id)
        if not subscribers:
            return
        if q in subscribers:
            subscribers.remove(q)
        if not subscribers:
            _subscribers.pop(workspace_id, None)


def publish_event(workspace_id: int, event_type: str, payload: dict) -> None:
    """Push an event to workspace subscribers (Redis when available)."""
    message = {"type": event_type, "payload": payload, "ts": time.time()}
    client = _get_redis()
    if client is not None:
        try:
            client.publish(_channel_name(workspace_id), json.dumps(message))
            return
        except Exception as exc:  # noqa: BLE001
            logger.warning("Redis publish failed, falling back to local: %s", exc)
    _local_publish(workspace_id, message)


def event_stream(workspace_id: int, q: queue.Queue, *, heartbeat_seconds: int = HEARTBEAT_SECONDS):
    """Generator yielding SSE-formatted text for a subscriber queue."""
    yield "retry: 3000\n\n"
    while True:
        try:
            message = q.get(timeout=heartbeat_seconds)
        except queue.Empty:
            yield ": heartbeat\n\n"
            continue
        yield f"event: {message['type']}\ndata: {json.dumps(message['payload'])}\n\n"


def reset_redis_state_for_tests() -> None:
    """Clear cached redis client (tests may toggle REDIS_URL)."""
    global _redis_client, _redis_checked
    with _lock:
        _redis_client = None
        _redis_checked = False
        _redis_listeners.clear()
