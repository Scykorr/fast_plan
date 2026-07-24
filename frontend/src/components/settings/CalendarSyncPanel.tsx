import { useCallback, useEffect, useState } from "react";

import { parseApiError } from "../../api/errors";
import { request } from "../../api/client";
import { ErrorMessage } from "../ErrorMessage";
import { useWorkspace } from "../../context/WorkspaceContext";

type Connection = {
  id: number;
  provider: string;
  last_synced_at: string | null;
  last_error: string;
  configured: boolean;
};

type Providers = { microsoft: boolean; google: boolean };

export function CalendarSyncPanel() {
  const { activeWorkspace } = useWorkspace();
  const [providers, setProviders] = useState<Providers>({
    microsoft: false,
    google: false,
  });
  const [connections, setConnections] = useState<Connection[]>([]);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    try {
      const [p, c] = await Promise.all([
        request<Providers>("/crm/calendar/providers/", {}),
        request<Connection[]>("/crm/calendar/connections/", {}),
      ]);
      setProviders(p);
      setConnections(c);
    } catch (err) {
      setError(parseApiError(err));
    }
  }, []);

  useEffect(() => {
    void load();
    const params = new URLSearchParams(window.location.search);
    if (params.get("cal_connected")) {
      setMessage(`Календарь ${params.get("cal_connected")} подключён`);
    }
    if (params.get("cal_error")) {
      setError(`Ошибка OAuth календаря: ${params.get("cal_error")}`);
    }
  }, [load]);

  const connectHref = (provider: "microsoft" | "google") =>
    `/api/crm/calendar/oauth/${provider}/`;

  return (
    <section className="rounded-xl border border-border bg-surface p-5">
      <h2 className="text-lg font-semibold text-text">Календарь CRM → Google / Outlook</h2>
      <p className="mt-1 text-sm text-text-muted">
        Односторонняя выгрузка задач сделок и встреч в внешний календарь (workspace:{" "}
        {activeWorkspace?.name || "—"}).
      </p>
      <ErrorMessage message={error} onDismiss={() => setError("")} />
      {message && (
        <p className="mt-2 text-sm text-secondary" role="status">
          {message}
        </p>
      )}
      <div className="mt-4 flex flex-wrap gap-2">
        {providers.microsoft && (
          <a
            href={connectHref("microsoft")}
            className="rounded-lg border border-border bg-cream px-3 py-2 text-sm font-medium hover:bg-surface"
          >
            Подключить Outlook
          </a>
        )}
        {providers.google && (
          <a
            href={connectHref("google")}
            className="rounded-lg border border-border bg-cream px-3 py-2 text-sm font-medium hover:bg-surface"
          >
            Подключить Google Calendar
          </a>
        )}
        {!providers.microsoft && !providers.google && (
          <p className="text-sm text-text-muted">
            Задайте OAUTH_MICROSOFT_* и/или OAUTH_GOOGLE_* в .env (отдельный consent с
            Calendars scope).
          </p>
        )}
      </div>
      <ul className="mt-4 space-y-2 text-sm">
        {connections.map((c) => (
          <li
            key={c.id}
            className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-border px-3 py-2"
          >
            <div>
              <strong>{c.provider}</strong>
              {c.last_synced_at && (
                <span className="ml-2 text-xs text-text-muted">
                  sync {new Date(c.last_synced_at).toLocaleString()}
                </span>
              )}
              {c.last_error && (
                <p className="text-xs text-primary">{c.last_error}</p>
              )}
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                disabled={loading}
                className="rounded-lg bg-primary px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-60"
                onClick={() =>
                  void (async () => {
                    setLoading(true);
                    setError("");
                    try {
                      const res = await request<{ ok: boolean; pushed?: number; error?: string }>(
                        `/crm/calendar/connections/${c.id}/sync/`,
                        { method: "POST", body: "{}" },
                      );
                      setMessage(
                        res.ok
                          ? `Синхронизировано: ${res.pushed ?? 0} событий`
                          : res.error || "Ошибка sync",
                      );
                      await load();
                    } catch (err) {
                      setError(parseApiError(err));
                    } finally {
                      setLoading(false);
                    }
                  })()
                }
              >
                Синхронизировать
              </button>
              <button
                type="button"
                className="rounded-lg border border-border px-3 py-1.5 text-xs"
                onClick={() =>
                  void (async () => {
                    try {
                      await request(`/crm/calendar/connections/${c.id}/`, {
                        method: "DELETE",
                      });
                      setMessage("Отключено");
                      await load();
                    } catch (err) {
                      setError(parseApiError(err));
                    }
                  })()
                }
              >
                Отключить
              </button>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
