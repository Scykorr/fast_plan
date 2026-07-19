import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import type { Notification } from "../api/notifications";
import { useNotificationsApi } from "../hooks/useNotificationsApi";

export function NotificationBell() {
  const api = useNotificationsApi();
  const [items, setItems] = useState<Notification[]>([]);
  const [open, setOpen] = useState(false);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);

  const load = useCallback(async () => {
    if (!api) {
      return;
    }
    try {
      const data = await api.getNotifications({ page: 1 });
      setItems(data.results);
      setHasMore(Boolean(data.next));
      setPage(1);
      setUnreadCount(data.results.filter((item) => !item.is_read).length);
    } catch {
      setItems([]);
      setHasMore(false);
    }
  }, [api]);

  useEffect(() => {
    void load();
  }, [load]);

  const handleLoadMore = async () => {
    if (!api || loadingMore) {
      return;
    }
    setLoadingMore(true);
    try {
      const nextPage = page + 1;
      const data = await api.getNotifications({ page: nextPage });
      setItems((current) => [...current, ...data.results]);
      setHasMore(Boolean(data.next));
      setPage(nextPage);
    } catch {
      setHasMore(false);
    } finally {
      setLoadingMore(false);
    }
  };

  const handleRead = async (item: Notification) => {
    if (!api || item.is_read) {
      return;
    }
    await api.markRead(item.id);
    void load();
  };

  const handleMarkAllRead = async () => {
    if (!api) {
      return;
    }
    await api.markAllRead();
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
        {unreadCount > 0 && (
          <span className="absolute -right-1 -top-1 rounded-full bg-primary px-1.5 text-[10px] font-bold text-white">
            {unreadCount}
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
            <div className="mb-2 flex items-center justify-between">
              <p className="text-sm font-semibold text-text">Уведомления</p>
              {items.some((item) => !item.is_read) && (
                <button
                  type="button"
                  onClick={() => void handleMarkAllRead()}
                  className="text-xs font-medium text-primary hover:underline"
                >
                  Прочитать все
                </button>
              )}
            </div>
            {items.length === 0 ? (
              <p className="text-xs text-text-muted">Пока пусто</p>
            ) : (
              <>
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
                {hasMore && (
                  <button
                    type="button"
                    onClick={() => void handleLoadMore()}
                    disabled={loadingMore}
                    className="mt-2 w-full rounded-lg border border-border py-1.5 text-xs text-text-muted hover:bg-cream disabled:opacity-60"
                  >
                    {loadingMore ? "Загрузка..." : "Показать ещё"}
                  </button>
                )}
              </>
            )}
          </div>
        </>
      )}
    </div>
  );
}
