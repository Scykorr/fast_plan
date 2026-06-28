import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import type { Notification } from "../api/notifications";
import { useNotificationsApi } from "../hooks/useNotificationsApi";

export function NotificationBell() {
  const api = useNotificationsApi();
  const [items, setItems] = useState<Notification[]>([]);
  const [open, setOpen] = useState(false);

  const load = useCallback(async () => {
    if (!api) {
      return;
    }
    try {
      setItems(await api.getNotifications());
    } catch {
      setItems([]);
    }
  }, [api]);

  useEffect(() => {
    void load();
  }, [load]);

  const unread = items.filter((item) => !item.is_read).length;

  const handleRead = async (item: Notification) => {
    if (!api || item.is_read) {
      return;
    }
    await api.markRead(item.id);
    void load();
  };

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="relative rounded-lg px-3 py-2 text-sm text-text-muted hover:bg-cream hover:text-text"
        aria-label="Уведомления"
      >
        🔔
        {unread > 0 && (
          <span className="absolute -right-1 -top-1 rounded-full bg-primary px-1.5 text-[10px] font-bold text-white">
            {unread}
          </span>
        )}
      </button>
      {open && (
        <>
          <button
            type="button"
            className="fixed inset-0 z-40"
            aria-label="Закрыть"
            onClick={() => setOpen(false)}
          />
          <div className="absolute right-0 z-50 mt-2 w-80 rounded-xl border border-border bg-surface p-3 shadow-lg">
            <p className="mb-2 text-sm font-semibold text-text">Уведомления</p>
            {items.length === 0 ? (
              <p className="text-xs text-text-muted">Пока пусто</p>
            ) : (
              <ul className="max-h-72 space-y-2 overflow-y-auto">
                {items.map((item) => (
                  <li key={item.id}>
                    <Link
                      to={item.link || "#"}
                      onClick={() => void handleRead(item)}
                      className={[
                        "block rounded-lg px-3 py-2 text-sm hover:bg-cream",
                        item.is_read ? "text-text-muted" : "font-medium text-text",
                      ].join(" ")}
                    >
                      <p>{item.title}</p>
                      {item.message && (
                        <p className="text-xs text-text-muted">{item.message}</p>
                      )}
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </>
      )}
    </div>
  );
}
