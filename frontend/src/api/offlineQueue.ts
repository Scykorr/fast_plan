/**
 * Offline mutation queue for CRM activities/tasks (P7 Mobile).
 * Persists to localStorage and replays when the browser is online.
 */

import { getActiveWorkspaceId, request } from "./client";

const STORAGE_KEY = "fp_offline_queue_v1";

export type QueuedMutation = {
  id: string;
  createdAt: string;
  workspaceId: number | null;
  kind: "crm.activity.create" | "crm.deal_task.create" | "crm.deal_task.patch";
  path: string;
  method: "POST" | "PATCH";
  body: Record<string, unknown>;
  label: string;
};

type QueueListener = (items: QueuedMutation[]) => void;

const listeners = new Set<QueueListener>();

function readQueue(): QueuedMutation[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return [];
    }
    const parsed = JSON.parse(raw) as QueuedMutation[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function writeQueue(items: QueuedMutation[]): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
  for (const listener of listeners) {
    listener(items);
  }
}

export function subscribeOfflineQueue(listener: QueueListener): () => void {
  listeners.add(listener);
  listener(readQueue());
  return () => {
    listeners.delete(listener);
  };
}

export function listOfflineQueue(): QueuedMutation[] {
  return readQueue();
}

export function enqueueOfflineMutation(
  item: Omit<QueuedMutation, "id" | "createdAt" | "workspaceId"> & {
    workspaceId?: number | null;
  },
): QueuedMutation {
  const entry: QueuedMutation = {
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
    createdAt: new Date().toISOString(),
    workspaceId:
      item.workspaceId !== undefined ? item.workspaceId : getActiveWorkspaceId(),
    kind: item.kind,
    path: item.path,
    method: item.method,
    body: item.body,
    label: item.label,
  };
  writeQueue([...readQueue(), entry]);
  return entry;
}

function isNetworkFailure(err: unknown): boolean {
  if (err instanceof TypeError) {
    return true;
  }
  if (err instanceof Error && /network|failed to fetch|offline/i.test(err.message)) {
    return true;
  }
  return false;
}

export type MutateResult<T> =
  | { queued: false; data: T }
  | { queued: true; entry: QueuedMutation };

/**
 * Run a mutating API call; if offline or network fails, enqueue for later.
 */
export async function mutateOrQueue<T>(options: {
  kind: QueuedMutation["kind"];
  path: string;
  method: "POST" | "PATCH";
  body: Record<string, unknown>;
  label: string;
  execute: () => Promise<T>;
}): Promise<MutateResult<T>> {
  if (typeof navigator !== "undefined" && navigator.onLine === false) {
    const entry = enqueueOfflineMutation({
      kind: options.kind,
      path: options.path,
      method: options.method,
      body: options.body,
      label: options.label,
    });
    return { queued: true, entry };
  }
  try {
    const data = await options.execute();
    return { queued: false, data };
  } catch (err) {
    if (isNetworkFailure(err)) {
      const entry = enqueueOfflineMutation({
        kind: options.kind,
        path: options.path,
        method: options.method,
        body: options.body,
        label: options.label,
      });
      return { queued: true, entry };
    }
    throw err;
  }
}

let flushing = false;

export async function flushOfflineQueue(): Promise<{
  sent: number;
  failed: number;
  remaining: number;
}> {
  if (flushing) {
    return { sent: 0, failed: 0, remaining: readQueue().length };
  }
  if (typeof navigator !== "undefined" && navigator.onLine === false) {
    return { sent: 0, failed: 0, remaining: readQueue().length };
  }
  flushing = true;
  let sent = 0;
  let failed = 0;
  try {
    const pending = readQueue();
    const remaining: QueuedMutation[] = [];
    for (const item of pending) {
      try {
        await request(item.path, {
          method: item.method,
          body: JSON.stringify(item.body),
          headers:
            item.workspaceId != null
              ? { "X-Workspace-Id": String(item.workspaceId) }
              : undefined,
        });
        sent += 1;
      } catch (err) {
        if (isNetworkFailure(err)) {
          remaining.push(item, ...pending.slice(pending.indexOf(item) + 1));
          break;
        }
        // Drop permanently failing items (4xx) after counting as failed
        failed += 1;
      }
    }
    writeQueue(remaining);
    return { sent, failed, remaining: remaining.length };
  } finally {
    flushing = false;
  }
}

export function startOfflineQueueAutoFlush(): () => void {
  const onOnline = () => {
    void flushOfflineQueue();
  };
  window.addEventListener("online", onOnline);
  void flushOfflineQueue();
  return () => window.removeEventListener("online", onOnline);
}
