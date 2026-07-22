import { useEffect, useState } from "react";

import {
  flushOfflineQueue,
  listOfflineQueue,
  startOfflineQueueAutoFlush,
  subscribeOfflineQueue,
  type QueuedMutation,
} from "../api/offlineQueue";

export function OfflineQueueBanner() {
  const [items, setItems] = useState<QueuedMutation[]>(() => listOfflineQueue());
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("");

  useEffect(() => subscribeOfflineQueue(setItems), []);

  useEffect(() => startOfflineQueueAutoFlush(), []);

  if (items.length === 0) {
    return null;
  }

  return (
    <div className="fixed bottom-4 left-4 z-50 max-w-sm rounded-xl border border-border bg-surface p-4 shadow-lg">
      <p className="text-sm font-medium text-text">
        Офлайн-очередь: {items.length}
      </p>
      <p className="mt-1 text-xs text-text-muted">
        CRM-действия сохранятся и отправятся при появлении сети.
      </p>
      <ul className="mt-2 max-h-24 space-y-1 overflow-y-auto text-xs text-text-muted">
        {items.slice(0, 5).map((item) => (
          <li key={item.id} className="truncate">
            {item.label}
          </li>
        ))}
      </ul>
      {status && (
        <p className="mt-2 text-xs text-secondary" role="status">
          {status}
        </p>
      )}
      <button
        type="button"
        disabled={busy}
        className="mt-3 rounded-lg bg-primary px-3 py-1.5 text-xs font-semibold text-white hover:bg-primary-hover disabled:opacity-60"
        onClick={() =>
          void (async () => {
            setBusy(true);
            setStatus("");
            try {
              const result = await flushOfflineQueue();
              setStatus(
                result.remaining === 0
                  ? `Отправлено: ${result.sent}`
                  : `Отправлено ${result.sent}, осталось ${result.remaining}`,
              );
            } finally {
              setBusy(false);
            }
          })()
        }
      >
        {busy ? "Отправка…" : "Синхронизировать сейчас"}
      </button>
    </div>
  );
}
