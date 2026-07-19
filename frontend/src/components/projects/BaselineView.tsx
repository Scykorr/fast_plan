import { useEffect, useState, type FormEvent } from "react";

import type { CriticalPath, ProjectBaseline, ProjectSchedule } from "../../api/projects";

type BaselineViewProps = {
  baselines: ProjectBaseline[];
  schedule: ProjectSchedule | null;
  onCreate: (name?: string) => Promise<void> | void;
  onRename: (id: number, name: string) => Promise<void> | void;
  onDelete: (id: number) => Promise<void> | void;
};

const inputClass =
  "w-full rounded-lg border border-border bg-cream px-3 py-2 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20";

export function BaselineView({
  baselines,
  schedule,
  onCreate,
  onRename,
  onDelete,
}: BaselineViewProps) {
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [selectedId, setSelectedId] = useState<number | null>(baselines[0]?.id ?? null);
  const [renaming, setRenaming] = useState(false);
  const [renameValue, setRenameValue] = useState("");
  const [renameError, setRenameError] = useState("");
  const [renameLoading, setRenameLoading] = useState(false);

  useEffect(() => {
    if (baselines.length === 0) {
      setSelectedId(null);
      return;
    }
    if (!baselines.some((item) => item.id === selectedId)) {
      setSelectedId(baselines[0].id);
    }
  }, [baselines, selectedId]);

  const selected = baselines.find((item) => item.id === selectedId) ?? baselines[0];

  useEffect(() => {
    setRenaming(false);
    setRenameValue(selected?.name ?? "");
  }, [selected?.id, selected?.name]);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      await onCreate(name.trim() || undefined);
      setName("");
      setShowForm(false);
    } catch {
      setError("Не удалось создать baseline");
    } finally {
      setLoading(false);
    }
  };

  const handleRenameSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (!selected) {
      return;
    }
    if (!renameValue.trim()) {
      setRenameError("Укажите название");
      return;
    }
    setRenameLoading(true);
    setRenameError("");
    try {
      await onRename(selected.id, renameValue.trim());
      setRenaming(false);
    } catch {
      setRenameError("Не удалось переименовать baseline");
    } finally {
      setRenameLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!selected) {
      return;
    }
    await onDelete(selected.id);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-text">Baseline</h2>
        <button
          type="button"
          onClick={() => setShowForm((value) => !value)}
          className="rounded-lg bg-secondary px-3 py-1.5 text-sm font-semibold text-white hover:opacity-90"
        >
          {showForm ? "Скрыть" : "Зафиксировать baseline"}
        </button>
      </div>

      {showForm && (
        <form
          onSubmit={handleSubmit}
          noValidate
          className="max-w-md space-y-3 rounded-xl border border-dashed border-border bg-surface p-4"
        >
          <div>
            <label htmlFor="baseline-name" className="mb-1 block text-sm font-medium">
              Название (необязательно)
            </label>
            <input
              id="baseline-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className={inputClass}
              autoFocus
              placeholder="Baseline 1"
            />
          </div>
          {error && (
            <p className="text-sm text-primary" role="alert">
              {error}
            </p>
          )}
          <button
            type="submit"
            disabled={loading}
            className="rounded-lg bg-secondary px-3 py-1.5 text-sm font-semibold text-white hover:opacity-90 disabled:opacity-60"
          >
            {loading ? "Сохранение..." : "Зафиксировать"}
          </button>
        </form>
      )}

      {baselines.length === 0 || !selected ? (
        <p className="text-sm text-text-muted">
          Снимок расписания ещё не создан. Зафиксируйте baseline для сравнения plan vs
          actual.
        </p>
      ) : (
        <div className="rounded-xl border border-border bg-surface p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <label className="flex items-center gap-2 text-sm text-text-muted">
              Сравнить с
              <select
                value={selected.id}
                onChange={(e) => setSelectedId(Number(e.target.value))}
                className="rounded-lg border border-border bg-cream px-2 py-1.5 text-sm text-text"
                aria-label="Выбор baseline"
              >
                {baselines.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name} · {new Date(item.created_at).toLocaleDateString("ru-RU")}
                  </option>
                ))}
              </select>
            </label>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setRenaming((value) => !value)}
                className="text-sm font-medium text-primary hover:underline"
              >
                Переименовать
              </button>
              <button
                type="button"
                onClick={() => void handleDelete()}
                className="text-sm text-text-muted hover:text-primary"
              >
                Удалить
              </button>
            </div>
          </div>

          {renaming && (
            <form
              onSubmit={handleRenameSubmit}
              noValidate
              className="mt-3 flex flex-wrap items-end gap-2"
            >
              <div className="min-w-48 flex-1">
                <label htmlFor="baseline-rename" className="mb-1 block text-xs font-medium">
                  Новое название
                </label>
                <input
                  id="baseline-rename"
                  value={renameValue}
                  onChange={(e) => setRenameValue(e.target.value)}
                  className={inputClass}
                  autoFocus
                />
              </div>
              <button
                type="submit"
                disabled={renameLoading}
                className="rounded-lg bg-primary px-3 py-1.5 text-sm font-semibold text-white hover:bg-primary-hover disabled:opacity-60"
              >
                {renameLoading ? "..." : "Сохранить"}
              </button>
              <button
                type="button"
                onClick={() => setRenaming(false)}
                className="rounded-lg border border-border px-3 py-1.5 text-sm text-text-muted hover:bg-cream"
              >
                Отмена
              </button>
              {renameError && (
                <p className="w-full text-sm text-primary" role="alert">
                  {renameError}
                </p>
              )}
            </form>
          )}

          <p className="mt-3 text-sm text-text-muted">
            <span className="font-medium text-text">{selected.name}</span> ·{" "}
            {new Date(selected.created_at).toLocaleString("ru-RU")}
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
                {selected.activities.map((item) => {
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
