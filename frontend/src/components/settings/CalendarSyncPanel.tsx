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
  conflict_policy: "ours" | "theirs" | "manual";
  open_conflicts: number;
};

type Conflict = {
  id: number;
  connection_id: number;
  provider: string;
  external_event_id: string;
  local_title: string;
  external_title: string;
  local_start: string | null;
  external_start: string | null;
};

type Providers = { microsoft: boolean; google: boolean };

type SyncResult = {
  ok: boolean;
  pushed?: number;
  imported?: number;
  updated?: number;
  conflicts?: number;
  error?: string;
};

export function CalendarSyncPanel() {
  const { activeWorkspace } = useWorkspace();
  const [providers, setProviders] = useState<Providers>({
    microsoft: false,
    google: false,
  });
  const [connections, setConnections] = useState<Connection[]>([]);
  const [conflicts, setConflicts] = useState<Conflict[]>([]);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    try {
      const [p, c, cf] = await Promise.all([
        request<Providers>("/crm/calendar/providers/", {}),
        request<Connection[]>("/crm/calendar/connections/", {}),
        request<Conflict[]>("/crm/calendar/conflicts/", {}),
      ]);
      setProviders(p);
      setConnections(c);
      setConflicts(cf);
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

  const runSync = async (id: number, direction: "both" | "push" | "pull") => {
    setLoading(true);
    setError("");
    try {
      const res = await request<SyncResult>(`/crm/calendar/connections/${id}/sync/`, {
        method: "POST",
        body: JSON.stringify({ direction }),
      });
      if (!res.ok) {
        setMessage(res.error || "Ошибка sync");
      } else {
        setMessage(
          `Sync (${direction}): push ${res.pushed ?? 0}, import ${res.imported ?? 0}` +
            (res.updated ? `, update ${res.updated}` : "") +
            (res.conflicts ? `, conflicts ${res.conflicts}` : ""),
        );
      }
      await load();
    } catch (err) {
      setError(parseApiError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="rounded-xl border border-border bg-surface p-5">
      <h2 className="text-lg font-semibold text-text">Календарь CRM ↔ Google / Outlook</h2>
      <p className="mt-1 text-sm text-text-muted">
        Двусторонняя синхронизация задач сделок и встреч (workspace:{" "}
        {activeWorkspace?.name || "—"}). Политика конфликтов: ours / theirs / manual.
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
            <div className="min-w-0 flex-1">
              <strong>{c.provider}</strong>
              {c.last_synced_at && (
                <span className="ml-2 text-xs text-text-muted">
                  sync {new Date(c.last_synced_at).toLocaleString()}
                </span>
              )}
              {c.open_conflicts > 0 && (
                <span className="ml-2 text-xs text-primary">
                  конфликтов: {c.open_conflicts}
                </span>
              )}
              {c.last_error && <p className="text-xs text-primary">{c.last_error}</p>}
              <label className="mt-1 flex items-center gap-2 text-xs text-text-muted">
                Конфликты:
                <select
                  value={c.conflict_policy || "ours"}
                  className="rounded border border-border bg-cream px-1.5 py-0.5 text-xs text-text"
                  onChange={(e) =>
                    void (async () => {
                      try {
                        await request(`/crm/calendar/connections/${c.id}/`, {
                          method: "PATCH",
                          body: JSON.stringify({
                            conflict_policy: e.target.value,
                          }),
                        });
                        await load();
                      } catch (err) {
                        setError(parseApiError(err));
                      }
                    })()
                  }
                >
                  <option value="ours">ours (Fast Plan)</option>
                  <option value="theirs">theirs (внешний)</option>
                  <option value="manual">manual (очередь)</option>
                </select>
              </label>
            </div>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                disabled={loading}
                className="rounded-lg bg-primary px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-60"
                onClick={() => void runSync(c.id, "both")}
              >
                Sync both
              </button>
              <button
                type="button"
                disabled={loading}
                className="rounded-lg border border-border px-3 py-1.5 text-xs disabled:opacity-60"
                onClick={() => void runSync(c.id, "pull")}
              >
                Pull
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
      {conflicts.length > 0 && (
        <div className="mt-4 space-y-2">
          <h3 className="text-sm font-semibold text-text">Открытые конфликты</h3>
          <ul className="space-y-2 text-sm">
            {conflicts.map((cf) => (
              <li
                key={cf.id}
                className="rounded-lg border border-border px-3 py-2"
              >
                <p className="font-medium">
                  {cf.provider}: «{cf.local_title || "—"}» ↔ «{cf.external_title || "—"}»
                </p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {(["ours", "theirs", "dismiss"] as const).map((choice) => (
                    <button
                      key={choice}
                      type="button"
                      className="rounded border border-border px-2 py-1 text-xs"
                      onClick={() =>
                        void (async () => {
                          try {
                            await request(
                              `/crm/calendar/conflicts/${cf.id}/resolve/`,
                              {
                                method: "POST",
                                body: JSON.stringify({ choice }),
                              },
                            );
                            setMessage(`Конфликт #${cf.id}: ${choice}`);
                            await load();
                          } catch (err) {
                            setError(parseApiError(err));
                          }
                        })()
                      }
                    >
                      {choice}
                    </button>
                  ))}
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
