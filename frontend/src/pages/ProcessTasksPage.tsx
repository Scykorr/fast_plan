import { useCallback, useEffect, useState } from "react";

import { parseApiError } from "../api/errors";
import type { ProcessUserTask } from "../api/process";
import { ErrorMessage } from "../components/ErrorMessage";
import { useProcessApi } from "../hooks/useProcessApi";
import { useWorkspace } from "../context/WorkspaceContext";

export function ProcessTasksPage() {
  const api = useProcessApi();
  const { workspaceEpoch } = useWorkspace();
  const [tasks, setTasks] = useState<ProcessUserTask[]>([]);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [formNote, setFormNote] = useState("");

  const load = useCallback(async () => {
    if (!api) return;
    try {
      setTasks(await api.listTasks({ status: "open" }));
    } catch (err) {
      setError(parseApiError(err));
    }
  }, [api]);

  useEffect(() => {
    void load();
  }, [load, workspaceEpoch]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-text">Задачи процессов</h1>
        <p className="mt-1 text-sm text-text-muted">
          Inbox user tasks (BPMN). Форма: note + произвольные поля из schema.
        </p>
      </div>
      <ErrorMessage message={error} />
      {message && (
        <p className="text-sm text-secondary" role="status">
          {message}
        </p>
      )}
      <ul className="space-y-3">
        {tasks.map((task) => (
          <li
            key={task.id}
            className="rounded-xl border border-border bg-surface p-4"
          >
            <p className="font-semibold text-text">{task.name}</p>
            <p className="text-xs text-text-muted">
              {task.definition_name} · instance #{task.instance_id}
              {task.due_at ? ` · due ${new Date(task.due_at).toLocaleString()}` : ""}
            </p>
            {Object.keys(task.form_schema || {}).length > 0 && (
              <pre className="mt-2 overflow-x-auto rounded bg-cream p-2 text-xs">
                {JSON.stringify(task.form_schema, null, 2)}
              </pre>
            )}
            <div className="mt-3 flex flex-wrap items-end gap-2">
              <input
                className="min-w-[12rem] flex-1 rounded-lg border border-border bg-cream px-3 py-2 text-sm"
                placeholder="Комментарий / form note"
                value={formNote}
                onChange={(e) => setFormNote(e.target.value)}
              />
              <button
                type="button"
                className="rounded-lg bg-primary px-3 py-2 text-sm font-semibold text-white"
                onClick={() =>
                  void (async () => {
                    if (!api) return;
                    try {
                      await api.completeTask(task.id, {
                        note: formNote,
                        approved: true,
                      });
                      setFormNote("");
                      setMessage(`Задача #${task.id} завершена`);
                      await load();
                    } catch (err) {
                      setError(parseApiError(err));
                    }
                  })()
                }
              >
                Завершить
              </button>
            </div>
          </li>
        ))}
        {tasks.length === 0 && (
          <li className="text-sm text-text-muted">Нет открытых задач</li>
        )}
      </ul>
    </div>
  );
}
