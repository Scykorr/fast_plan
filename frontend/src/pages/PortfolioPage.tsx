import { Link } from "react-router-dom";
import { useCallback, useEffect, useState } from "react";

import { parseApiError } from "../api/errors";
import type { WorkspaceDashboard } from "../api/workspace";
import { ErrorMessage } from "../components/ErrorMessage";
import { ChatPanel } from "../components/chats/ChatPanel";
import { useWorkspace } from "../context/WorkspaceContext";
import { useLocale } from "../context/LocaleContext";
import { useAuth } from "../context/AuthContext";
import { useWorkspaceApi } from "../hooks/useWorkspaceApi";

export function PortfolioPage() {
  const workspaceApi = useWorkspaceApi();
  const { workspaceEpoch, activeWorkspace } = useWorkspace();
  const { isAuthenticated } = useAuth();
  const { formatMoney, currency, baseCurrency } = useLocale();
  const [dashboard, setDashboard] = useState<WorkspaceDashboard | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!workspaceApi) {
      return;
    }
    setLoading(true);
    setError("");
    try {
      setDashboard(await workspaceApi.getDashboard());
    } catch (err) {
      setError(parseApiError(err, "Не удалось загрузить портфель"));
    } finally {
      setLoading(false);
    }
  }, [workspaceApi]);

  useEffect(() => {
    void load();
  }, [load, workspaceEpoch]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-text">Портфель</h1>
        <p className="mt-1 text-sm text-text-muted">
          Сводка по проектам workspace
          {activeWorkspace ? ` «${activeWorkspace.name}»` : ""}
          {currency !== baseCurrency && (
            <> · суммы в {currency}, база {baseCurrency}</>
          )}
        </p>
      </div>

      {error && <ErrorMessage message={error} onDismiss={() => setError("")} />}

      {loading || !dashboard ? (
        <p className="text-text-muted">Загрузка...</p>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-4">
            <div className="rounded-xl border border-border bg-surface p-5">
              <p className="text-sm text-text-muted">Проекты</p>
              <p className="mt-1 text-3xl font-bold text-text">
                {dashboard.summary.project_count}
              </p>
            </div>
            <div className="rounded-xl border border-border bg-surface p-5">
              <p className="text-sm text-text-muted">Просрочки</p>
              <p className="mt-1 text-3xl font-bold text-primary">
                {dashboard.summary.overdue_count}
              </p>
            </div>
            <div className="rounded-xl border border-border bg-surface p-5">
              <p className="text-sm text-text-muted">Открытые риски</p>
              <p className="mt-1 text-3xl font-bold text-text">
                {dashboard.summary.open_risk_count}
              </p>
            </div>
            <div className="rounded-xl border border-border bg-surface p-5">
              <p className="text-sm text-text-muted">Непрочитанные</p>
              <p className="mt-1 text-3xl font-bold text-secondary">
                {dashboard.summary.unread_notification_count}
              </p>
            </div>
          </div>

          <div className="overflow-x-auto rounded-xl border border-border bg-surface">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-cream text-left text-text-muted">
                  <th className="px-4 py-3">Проект</th>
                  <th className="px-4 py-3">Статус</th>
                  <th className="px-4 py-3">Прогресс</th>
                  <th className="px-4 py-3">Бюджет</th>
                  <th className="px-4 py-3">SPI</th>
                  <th className="px-4 py-3">CPI</th>
                  <th className="px-4 py-3">Просрочки</th>
                </tr>
              </thead>
              <tbody>
                {dashboard.project_health.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-4 py-6 text-text-muted">
                      Нет активных проектов
                    </td>
                  </tr>
                ) : (
                  dashboard.project_health.map((row) => (
                    <tr key={row.project_id} className="border-b border-border/60">
                      <td className="px-4 py-3">
                        <Link
                          to={`/projects/${row.project_id}`}
                          className="font-medium text-primary hover:underline"
                        >
                          {row.name}
                        </Link>
                      </td>
                      <td className="px-4 py-3 text-text-muted">{row.status}</td>
                      <td className="px-4 py-3">{row.progress}%</td>
                      <td className="px-4 py-3">
                        {formatMoney(row.budget)}
                      </td>
                      <td className="px-4 py-3">{row.spi ?? "—"}</td>
                      <td className="px-4 py-3">{row.cpi ?? "—"}</td>
                      <td className="px-4 py-3 font-medium text-primary">
                        {row.overdue_count}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {isAuthenticated && (
            <div className="space-y-2">
              <h2 className="text-xl font-semibold text-text">Чат портфеля</h2>
              <p className="text-sm text-text-muted">
                Общение участников workspace. Руководитель может выключить чат,
                включить режим оповещений или запретить писать отдельным людям.
              </p>
              <ChatPanel scope="workspace" />
            </div>
          )}
        </>
      )}
    </div>
  );
}
