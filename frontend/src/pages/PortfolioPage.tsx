import { Link } from "react-router-dom";
import { useCallback, useEffect, useState } from "react";

import { parseApiError } from "../api/errors";
import type {
  CrossProjectDependency,
  WorkspaceScheduleActivity,
} from "../api/projects";
import type { WorkspaceDashboard } from "../api/workspace";
import { ErrorMessage } from "../components/ErrorMessage";
import { TermHint } from "../components/TermHint";
import { ChatPanel } from "../components/chats/ChatPanel";
import { useWorkspace } from "../context/WorkspaceContext";
import { useLocale } from "../context/LocaleContext";
import { useAuth } from "../context/AuthContext";
import { useProjectsApi } from "../hooks/useProjectsApi";
import { useWorkspaceApi } from "../hooks/useWorkspaceApi";

export function PortfolioPage() {
  const workspaceApi = useWorkspaceApi();
  const projectsApi = useProjectsApi();
  const { workspaceEpoch, activeWorkspace } = useWorkspace();
  const { isAuthenticated } = useAuth();
  const { formatMoney, currency, baseCurrency } = useLocale();
  const [dashboard, setDashboard] = useState<WorkspaceDashboard | null>(null);
  const [crossDeps, setCrossDeps] = useState<CrossProjectDependency[]>([]);
  const [scheduleActivities, setScheduleActivities] = useState<
    WorkspaceScheduleActivity[]
  >([]);
  const [crossForm, setCrossForm] = useState({
    predecessor_id: "",
    successor_id: "",
    dependency_type: "FS",
    lag_days: "0",
    note: "",
  });
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!workspaceApi) {
      return;
    }
    setLoading(true);
    setError("");
    try {
      setDashboard(await workspaceApi.getDashboard());
      if (projectsApi) {
        const [deps, activities] = await Promise.all([
          projectsApi.listCrossDependencies(),
          projectsApi.listWorkspaceScheduleActivities(),
        ]);
        setCrossDeps(deps);
        setScheduleActivities(activities);
      }
    } catch (err) {
      setError(parseApiError(err, "Не удалось загрузить портфель"));
    } finally {
      setLoading(false);
    }
  }, [workspaceApi, projectsApi]);

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
                  <th className="px-4 py-3">
                    <TermHint term="spi">SPI</TermHint>
                  </th>
                  <th className="px-4 py-3">
                    <TermHint term="spi(t)">SPI(t)</TermHint>
                  </th>
                  <th className="px-4 py-3">
                    <TermHint term="cpi">CPI</TermHint>
                  </th>
                  <th className="px-4 py-3">Просрочки</th>
                </tr>
              </thead>
              <tbody>
                {dashboard.project_health.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="px-4 py-6 text-text-muted">
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
                      <td className="px-4 py-3">{row.spi_t ?? "—"}</td>
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

          <section className="space-y-3 rounded-xl border border-border bg-surface p-4">
            <h2 className="text-base font-semibold text-text">
              Cross-project зависимости
            </h2>
            <p className="text-xs text-text-muted">
              Мягкие связи между schedule activity разных проектов (не входят в
              CPM). Выберите активности из списка.
            </p>
            {message && (
              <p className="text-sm text-secondary" role="status">
                {message}
              </p>
            )}
            <form
              className="grid gap-2 sm:grid-cols-5"
              onSubmit={(e) => {
                e.preventDefault();
                if (!projectsApi) return;
                const pred = Number(crossForm.predecessor_id);
                const succ = Number(crossForm.successor_id);
                if (!Number.isFinite(pred) || !Number.isFinite(succ)) {
                  setError("Выберите predecessor и successor");
                  return;
                }
                void projectsApi
                  .createCrossDependency({
                    predecessor_id: pred,
                    successor_id: succ,
                    dependency_type: crossForm.dependency_type,
                    lag_days: Number(crossForm.lag_days) || 0,
                    note: crossForm.note,
                  })
                  .then(() => {
                    setMessage("Связь сохранена");
                    setCrossForm({
                      predecessor_id: "",
                      successor_id: "",
                      dependency_type: "FS",
                      lag_days: "0",
                      note: "",
                    });
                    return load();
                  })
                  .catch((err) =>
                    setError(parseApiError(err, "Не удалось создать связь")),
                  );
              }}
            >
              <select
                value={crossForm.predecessor_id}
                onChange={(e) =>
                  setCrossForm({ ...crossForm, predecessor_id: e.target.value })
                }
                className="rounded border border-border bg-cream px-2 py-1.5 text-sm"
                required
              >
                <option value="">Predecessor…</option>
                {scheduleActivities.map((a) => (
                  <option key={`p-${a.id}`} value={a.id}>
                    P{a.project_id}/{a.code} {a.name}
                  </option>
                ))}
              </select>
              <select
                value={crossForm.successor_id}
                onChange={(e) =>
                  setCrossForm({ ...crossForm, successor_id: e.target.value })
                }
                className="rounded border border-border bg-cream px-2 py-1.5 text-sm"
                required
              >
                <option value="">Successor…</option>
                {scheduleActivities.map((a) => (
                  <option key={`s-${a.id}`} value={a.id}>
                    P{a.project_id}/{a.code} {a.name}
                  </option>
                ))}
              </select>
              <select
                value={crossForm.dependency_type}
                onChange={(e) =>
                  setCrossForm({
                    ...crossForm,
                    dependency_type: e.target.value,
                  })
                }
                className="rounded border border-border bg-cream px-2 py-1.5 text-sm"
              >
                {["FS", "SS", "FF", "SF"].map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
              <input
                value={crossForm.lag_days}
                onChange={(e) =>
                  setCrossForm({ ...crossForm, lag_days: e.target.value })
                }
                placeholder="lag days"
                className="rounded border border-border bg-cream px-2 py-1.5 text-sm"
              />
              <button
                type="submit"
                className="rounded-lg bg-primary px-3 py-1.5 text-sm font-semibold text-white"
              >
                Добавить
              </button>
            </form>
            <ul className="max-h-48 space-y-1 overflow-y-auto text-sm">
              {crossDeps.length === 0 ? (
                <li className="text-text-muted">Пока нет связей</li>
              ) : (
                crossDeps.map((dep) => (
                  <li
                    key={dep.id}
                    className="flex flex-wrap items-center justify-between gap-2 rounded border border-border px-2 py-1.5"
                  >
                    <span>
                      #{dep.id} · P{dep.predecessor_project_id}/
                      {dep.predecessor_title || dep.predecessor_id} → P
                      {dep.successor_project_id}/
                      {dep.successor_title || dep.successor_id} ·{" "}
                      {dep.dependency_type}
                      {dep.lag_days ? ` +${dep.lag_days}д` : ""}
                    </span>
                    <button
                      type="button"
                      className="text-xs text-text-muted hover:text-primary"
                      onClick={() => {
                        if (!projectsApi) return;
                        void projectsApi
                          .deleteCrossDependency(dep.id)
                          .then(() => load())
                          .catch((err) =>
                            setError(
                              parseApiError(err, "Не удалось удалить"),
                            ),
                          );
                      }}
                    >
                      Удалить
                    </button>
                  </li>
                ))
              )}
            </ul>
          </section>

          {isAuthenticated && (
            <div className="space-y-2">
              <h2 className="text-base font-semibold text-text">Чат портфеля</h2>
              <ChatPanel scope="workspace" />
            </div>
          )}
        </>
      )}
    </div>
  );
}
