import { useCallback, useEffect, useState } from "react";

import type { AuditLogEntry } from "../api/audit";
import { parseApiError } from "../api/errors";
import { ErrorMessage } from "../components/ErrorMessage";
import { useWorkspace } from "../context/WorkspaceContext";
import { useAuditApi } from "../hooks/useAuditApi";

const PAGE_SIZE = 50;

export function AuditPage() {
  const auditApi = useAuditApi();
  const { workspaceEpoch, activeWorkspace } = useWorkspace();
  const [entries, setEntries] = useState<AuditLogEntry[]>([]);
  const [count, setCount] = useState(0);
  const [page, setPage] = useState(1);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!auditApi) {
      return;
    }
    setLoading(true);
    setError("");
    try {
      const data = await auditApi.getAuditLog(page);
      setEntries(data.results);
      setCount(data.count);
    } catch (err) {
      setError(parseApiError(err, "Не удалось загрузить журнал аудита"));
    } finally {
      setLoading(false);
    }
  }, [auditApi, page]);

  useEffect(() => {
    setPage(1);
  }, [workspaceEpoch]);

  useEffect(() => {
    void load();
  }, [load, workspaceEpoch]);

  const totalPages = Math.max(1, Math.ceil(count / PAGE_SIZE));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-text">Журнал аудита</h1>
        <p className="mt-1 text-sm text-text-muted">
          История ключевых изменений workspace
          {activeWorkspace ? ` «${activeWorkspace.name}»` : ""}
        </p>
      </div>

      {error && <ErrorMessage message={error} onDismiss={() => setError("")} />}

      {loading ? (
        <p className="text-text-muted">Загрузка...</p>
      ) : entries.length === 0 ? (
        <p className="text-sm text-text-muted">Записей пока нет</p>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-border bg-surface">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-cream text-left text-text-muted">
                <th className="px-4 py-3">Дата</th>
                <th className="px-4 py-3">Автор</th>
                <th className="px-4 py-3">Действие</th>
                <th className="px-4 py-3">Объект</th>
                <th className="px-4 py-3">Описание</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((entry) => (
                <tr key={entry.id} className="border-b border-border/60 align-top">
                  <td className="whitespace-nowrap px-4 py-3 text-text-muted">
                    {new Date(entry.created_at).toLocaleString("ru-RU")}
                  </td>
                  <td className="px-4 py-3">{entry.actor_name ?? "Система"}</td>
                  <td className="px-4 py-3">
                    <span className="rounded-md bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
                      {entry.action}
                    </span>
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-text-muted">
                    {entry.entity_type} #{entry.entity_id}
                  </td>
                  <td className="px-4 py-3 text-text">{entry.summary}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {count > PAGE_SIZE && (
        <div className="flex items-center justify-between gap-3 text-sm">
          <button
            type="button"
            disabled={page <= 1}
            onClick={() => setPage((value) => Math.max(1, value - 1))}
            className="rounded-lg border border-border px-3 py-1.5 text-text-muted hover:bg-cream disabled:opacity-50"
          >
            Назад
          </button>
          <span className="text-text-muted">
            Страница {page} из {totalPages}
          </span>
          <button
            type="button"
            disabled={page >= totalPages}
            onClick={() => setPage((value) => Math.min(totalPages, value + 1))}
            className="rounded-lg border border-border px-3 py-1.5 text-text-muted hover:bg-cream disabled:opacity-50"
          >
            Далее
          </button>
        </div>
      )}
    </div>
  );
}
