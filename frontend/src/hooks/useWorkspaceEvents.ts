import { useEffect, useRef } from "react";

/**
 * Realtime workspace event types published by the backend (see
 * `workspaces/events.py` and callers of `publish_event`).
 */
export type WorkspaceEventType =
  | "wbs.updated"
  | "card.moved"
  | "comment.created"
  | "chat.message";

export type WorkspaceEventHandler = (
  type: WorkspaceEventType,
  payload: Record<string, unknown>,
) => void;

const EVENT_TYPES: WorkspaceEventType[] = [
  "wbs.updated",
  "card.moved",
  "comment.created",
  "chat.message",
];

/**
 * Subscribes to `GET /api/workspace/events/` (Server-Sent Events) using
 * cookie auth (EventSource cannot set custom headers/CSRF, so this relies on
 * the same HttpOnly JWT cookie regular GET requests use). Reconnects
 * automatically via the browser's built-in EventSource retry logic.
 *
 * Limitation: the backend pub/sub is in-process only (see
 * `workspaces/events.py` docstring), so this only sees events published in
 * the same server process the client happens to be connected to.
 */
export function useWorkspaceEvents(
  enabled: boolean,
  onEvent: WorkspaceEventHandler,
): void {
  const handlerRef = useRef(onEvent);
  handlerRef.current = onEvent;

  useEffect(() => {
    if (!enabled || typeof EventSource === "undefined") {
      return;
    }

    const source = new EventSource("/api/workspace/events/", {
      withCredentials: true,
    });

    const listeners = EVENT_TYPES.map((type) => {
      const listener = (event: MessageEvent) => {
        try {
          const payload = event.data ? JSON.parse(event.data) : {};
          handlerRef.current(type, payload);
        } catch {
          // Ignore malformed payloads.
        }
      };
      source.addEventListener(type, listener as EventListener);
      return { type, listener };
    });

    return () => {
      listeners.forEach(({ type, listener }) =>
        source.removeEventListener(type, listener as EventListener),
      );
      source.close();
    };
  }, [enabled]);
}
