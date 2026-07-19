import { Link } from "react-router-dom";
import { useEffect, useState } from "react";

import type { UpcomingBirthday } from "../api/calendar";
import { parseApiError } from "../api/errors";
import type { WorkspaceDashboard } from "../api/workspace";
import { ErrorMessage } from "../components/ErrorMessage";
import { UpcomingBirthdays } from "../components/calendar/UpcomingBirthdays";
import { useAuth } from "../context/AuthContext";
import { useWorkspace } from "../context/WorkspaceContext";
import { useCalendarApi } from "../hooks/useCalendarApi";
import { useWorkspaceApi } from "../hooks/useWorkspaceApi";

function metric(value: number | null | undefined) {
  if (value == null) {
    return "—";
  }
  return value.toFixed(2);
}

export function DashboardPage() {
  const { user } = useAuth();
  const { workspaceEpoch, activeWorkspace } = useWorkspace();
  const calendarApi = useCalendarApi();
  const workspaceApi = useWorkspaceApi();
  const [upcoming, setUpcoming] = useState<UpcomingBirthday[]>([]);
  const [dashboard, setDashboard] = useState<WorkspaceDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const load = async () => {
      if (!calendarApi || !workspaceApi) {
        return;
      }
      setLoading(true);
      try {
        const [birthdays, commandCenter] = await Promise.all([
          calendarApi.getUpcoming(5),
          workspaceApi.getDashboard(),
        ]);
        setUpcoming(birthdays);
        setDashboard(commandCenter);
      } catch (err) {
        setError(parseApiError(err, "Не удалось загрузить дашборд"));
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, [calendarApi, workspaceApi, workspaceEpoch, activeWorkspace?.id]);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-text">
          Привет{user?.first_name ? `, ${user.first_name}` : ""}!
        </h1>
        <p className="mt-2 text-text-muted">
          Командный центр
          {activeWorkspace ? ` · ${activeWorkspace.name}` : ""}
        </p>
      </div>

      <ErrorMessage message={error} onDismiss={() => setError("")} />

      {dashboard && (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {[
            ["Проекты", dashboard.summary.project_count],
            ["Просрочено", dashboard.summary.overdue_count],
            ["Открытые риски", dashboard.summary.open_risk_count],
            ["Непрочитанные", dashboard.summary.unread_notification_count],
          ].map(([label, value]) => (
            <div
              key={String(label)}
              className="rounded-xl border border-border bg-surface p-4"
            >
              <p className="text-xs text-text-muted">{label}</p>
              <p className="mt-1 text-2xl font-bold text-text">{value}</p>
            </div>
          ))}
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="rounded-xl border border-border bg-surface p-4">
          <h2 className="mb-3 text-lg font-semibold text-text">Просроченные задачи</h2>
          {loading && <p className="text-sm text-text-muted">Загрузка...</p>}
          {!loading && dashboard?.overdue_tasks.length === 0 && (
            <p className="text-sm text-text-muted">Просроченных задач нет</p>
          )}
          <ul className="space-y-2">
            {dashboard?.overdue_tasks.map((item) => (
              <li key={item.activity_id}>
                <Link
                  to={`/projects/${item.project_id}?tab=wbs&node=${item.wbs_id}&workspace=${dashboard.workspace_id}`}
                  className="block rounded-lg border border-border px-3 py-2 hover:bg-cream"
                >
                  <p className="text-sm font-medium text-text">
                    {item.wbs_code} {item.title}
                  </p>
                  <p className="text-xs text-text-muted">
                    {item.project_name} · {item.days_overdue} дн. · {item.progress}%
                  </p>
                </Link>
              </li>
            ))}
          </ul>
        </section>

        <section className="rounded-xl border border-border bg-surface p-4">
          <h2 className="mb-3 text-lg font-semibold text-text">Топ риски</h2>
          {!loading && dashboard?.top_risks.length === 0 && (
            <p className="text-sm text-text-muted">Открытых рисков нет</p>
          )}
          <ul className="space-y-2">
            {dashboard?.top_risks.map((risk) => (
              <li key={risk.id}>
                <Link
                  to={`/projects/${risk.project_id}?tab=risks&risk=${risk.id}&workspace=${dashboard.workspace_id}`}
                  className="block rounded-lg border border-border px-3 py-2 hover:bg-cream"
                >
                  <p className="text-sm font-medium text-text">{risk.title}</p>
                  <p className="text-xs text-text-muted">
                    {risk.project_name} · score {risk.score}
                  </p>
                </Link>
              </li>
            ))}
          </ul>
        </section>

        <section className="rounded-xl border border-border bg-surface p-4">
          <h2 className="mb-3 text-lg font-semibold text-text">Здоровье проектов</h2>
          {!loading && dashboard?.project_health.length === 0 && (
            <p className="text-sm text-text-muted">Активных проектов нет</p>
          )}
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="text-xs text-text-muted">
                <tr>
                  <th className="py-1 pr-3">Проект</th>
                  <th className="py-1 pr-3">SPI</th>
                  <th className="py-1 pr-3">CPI</th>
                  <th className="py-1">%</th>
                </tr>
              </thead>
              <tbody>
                {dashboard?.project_health.map((project) => (
                  <tr key={project.project_id} className="border-t border-border">
                    <td className="py-2 pr-3">
                      <Link
                        to={`/projects/${project.project_id}?workspace=${dashboard.workspace_id}`}
                        className="font-medium text-primary hover:underline"
                      >
                        {project.name}
                      </Link>
                      {project.overdue_count > 0 && (
                        <span className="ml-2 text-xs text-primary">
                          {project.overdue_count} overdue
                        </span>
                      )}
                    </td>
                    <td className="py-2 pr-3">{metric(project.spi)}</td>
                    <td className="py-2 pr-3">{metric(project.cpi)}</td>
                    <td className="py-2">{project.progress}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="rounded-xl border border-border bg-surface p-4">
          <h2 className="mb-3 text-lg font-semibold text-text">Непрочитанные</h2>
          {!loading && dashboard?.unread_notifications.length === 0 && (
            <p className="text-sm text-text-muted">Нет непрочитанных уведомлений</p>
          )}
          <ul className="space-y-2">
            {dashboard?.unread_notifications.map((item) => (
              <li key={item.id}>
                <Link
                  to={item.link || "/"}
                  className="block rounded-lg border border-border px-3 py-2 hover:bg-cream"
                >
                  <p className="text-sm font-medium text-text">{item.title}</p>
                  <p className="text-xs text-text-muted">{item.message}</p>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      </div>

      <section>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-text">Ближайшие дни рождения</h2>
          <Link to="/calendar" className="text-sm font-medium text-accent hover:underline">
            Календарь →
          </Link>
        </div>
        <UpcomingBirthdays items={upcoming} loading={loading} />
      </section>
    </div>
  );
}
