import type { CriticalPath, ProjectBaseline, ProjectSchedule } from "../../api/projects";

type BaselineViewProps = {
  baselines: ProjectBaseline[];
  schedule: ProjectSchedule | null;
  onCreate: () => void;
};

export function BaselineView({ baselines, schedule, onCreate }: BaselineViewProps) {
  const latest = baselines[0];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-text">Baseline</h2>
        <button
          type="button"
          onClick={onCreate}
          className="rounded-lg bg-secondary px-3 py-1.5 text-sm font-semibold text-white hover:opacity-90"
        >
          Зафиксировать baseline
        </button>
      </div>
      {baselines.length === 0 ? (
        <p className="text-sm text-text-muted">
          Снимок расписания ещё не создан. Зафиксируйте baseline для сравнения plan vs
          actual.
        </p>
      ) : (
        <div className="rounded-xl border border-border bg-surface p-4">
          <p className="text-sm text-text-muted">
            Последний: <span className="font-medium text-text">{latest.name}</span> ·{" "}
            {new Date(latest.created_at).toLocaleString("ru-RU")}
          </p>
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-text-muted">
                  <th className="py-2">WBS</th>
                  <th className="py-2">Baseline</th>
                  <th className="py-2">Факт</th>
                  <th className="py-2">Δ progress</th>
                </tr>
              </thead>
              <tbody>
                {latest.activities.map((item) => {
                  const actual = schedule?.activities.find(
                    (activity) => activity.id === item.activity_id,
                  );
                  const delta = actual ? actual.progress - item.progress : 0;
                  return (
                    <tr key={item.id} className="border-b border-border/60">
                      <td className="py-2 font-mono text-xs">
                        {item.wbs_code} {item.wbs_title}
                      </td>
                      <td className="py-2 text-text-muted">
                        {item.start_date} — {item.end_date} ({item.progress}%)
                      </td>
                      <td className="py-2">
                        {actual
                          ? `${actual.start_date} — ${actual.end_date} (${actual.progress}%)`
                          : "—"}
                      </td>
                      <td
                        className={[
                          "py-2 font-medium",
                          delta > 0 ? "text-secondary" : delta < 0 ? "text-primary" : "",
                        ].join(" ")}
                      >
                        {delta > 0 ? `+${delta}` : delta}%
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

type CriticalPathViewProps = {
  data: CriticalPath | null;
};

export function CriticalPathView({ data }: CriticalPathViewProps) {
  if (!data || data.activities.length === 0) {
    return (
      <p className="text-sm text-text-muted">
        Добавьте work packages и FS-зависимости для расчёта критического пути.
      </p>
    );
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="rounded-xl border border-border bg-surface p-4">
          <p className="text-sm text-text-muted">Длительность проекта</p>
          <p className="text-2xl font-bold text-text">{data.project_duration} дн.</p>
        </div>
        <div className="rounded-xl border border-border bg-surface p-4">
          <p className="text-sm text-text-muted">Критических задач</p>
          <p className="text-2xl font-bold text-primary">
            {data.critical_path_ids.length}
          </p>
        </div>
      </div>
      <div className="overflow-x-auto rounded-xl border border-border bg-surface">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-cream text-left text-text-muted">
              <th className="px-4 py-2">Задача</th>
              <th className="px-4 py-2">Длит.</th>
              <th className="px-4 py-2">ES</th>
              <th className="px-4 py-2">EF</th>
              <th className="px-4 py-2">Резерв</th>
            </tr>
          </thead>
          <tbody>
            {data.activities.map((activity) => (
              <tr
                key={activity.id}
                className={activity.is_critical ? "bg-primary/5" : ""}
              >
                <td className="px-4 py-2 font-mono text-xs">
                  {activity.code} {activity.name}
                </td>
                <td className="px-4 py-2">{activity.duration_days}</td>
                <td className="px-4 py-2">{activity.early_start}</td>
                <td className="px-4 py-2">{activity.early_finish}</td>
                <td className="px-4 py-2 font-medium">
                  {activity.slack}
                  {activity.is_critical && (
                    <span className="ml-2 text-xs text-primary">крит.</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
