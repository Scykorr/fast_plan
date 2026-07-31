import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { parseApiError } from "../api/errors";
import type { ProcessUserTask } from "../api/process";
import type { WBSNode } from "../api/projects";
import { ErrorMessage } from "../components/ErrorMessage";
import { useProcessApi } from "../hooks/useProcessApi";
import { useProjectsApi } from "../hooks/useProjectsApi";
import { useWorkspace } from "../context/WorkspaceContext";

function flattenWbs(nodes: WBSNode[], depth = 0): Array<WBSNode & { depth: number }> {
  const out: Array<WBSNode & { depth: number }> = [];
  for (const node of nodes) {
    out.push({ ...node, depth });
    if (node.children?.length) {
      out.push(...flattenWbs(node.children, depth + 1));
    }
  }
  return out;
}

export function ProcessTasksPage() {
  const api = useProcessApi();
  const projectsApi = useProjectsApi();
  const { workspaceEpoch } = useWorkspace();
  const [tasks, setTasks] = useState<ProcessUserTask[]>([]);
  const [wbsByProject, setWbsByProject] = useState<Record<number, WBSNode[]>>({});
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [notes, setNotes] = useState<Record<number, string>>({});
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    if (!api) return;
    setLoading(true);
    try {
      const rows = await api.listTasks({ status: "open" });
      setTasks(rows);
      if (projectsApi) {
        const projectIds = [
          ...new Set(rows.map((t) => t.project).filter((id): id is number => id != null)),
        ];
        const next: Record<number, WBSNode[]> = {};
        await Promise.all(
          projectIds.map(async (projectId) => {
            try {
              next[projectId] = await projectsApi.listWbs(projectId);
            } catch {
              next[projectId] = [];
            }
          }),
        );
        setWbsByProject(next);
      }
    } catch (err) {
      setError(parseApiError(err));
    } finally {
      setLoading(false);
    }
  }, [api, projectsApi]);

  useEffect(() => {
    void load();
  }, [load, workspaceEpoch]);

  const bind = async (task: ProcessUserTask, wbsNodeId: number | null) => {
    if (!api) return;
    try {
      const updated = await api.bindTask(task.id, wbsNodeId);
      setTasks((prev) => prev.map((t) => (t.id === task.id ? updated : t)));
      setMessage(
        wbsNodeId
          ? `Задача #${task.id} привязана к WBS`
          : `Привязка WBS снята с задачи #${task.id}`,
      );
    } catch (err) {
      setError(parseApiError(err));
    }
  };

  const complete = async (task: ProcessUserTask, approved: boolean) => {
    if (!api) return;
    try {
      await api.completeTask(task.id, {
        note: notes[task.id] || "",
        approved,
      });
      setNotes((prev) => {
        const next = { ...prev };
        delete next[task.id];
        return next;
      });
      setMessage(
        approved
          ? `Задача #${task.id} завершена (одобрено)`
          : `Задача #${task.id} завершена (отклонено)`,
      );
      await load();
    } catch (err) {
      setError(parseApiError(err));
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-text">Задачи процессов</h1>
          <p className="mt-1 text-sm text-text-muted">
            Inbox user tasks (BPMN). Привязка к WBS синхронизирует прогресс и Kanban при
            завершении.
          </p>
        </div>
        <Link to="/processes" className="text-sm text-primary hover:underline">
          К процессам →
        </Link>
      </div>
      <ErrorMessage message={error} />
      {message && (
        <p className="text-sm text-secondary" role="status">
          {message}
        </p>
      )}
      {loading && <p className="text-sm text-text-muted">Загрузка…</p>}
      <ul className="space-y-3">
        {tasks.map((task) => {
          const flat =
            task.project != null
              ? flattenWbs(wbsByProject[task.project] || [])
              : [];
          return (
            <li
              key={task.id}
              className="rounded-xl border border-border bg-surface p-4"
            >
              <p className="font-semibold text-text">{task.name}</p>
              <p className="text-xs text-text-muted">
                {task.definition_name} · instance #{task.instance_id}
                {task.due_at ? ` · due ${new Date(task.due_at).toLocaleString()}` : ""}
              </p>
              <div className="mt-1 flex flex-wrap gap-3 text-xs">
                {task.deal != null && (
                  <Link
                    className="text-primary hover:underline"
                    to={`/deals?deal=${task.deal}`}
                  >
                    Сделка #{task.deal}
                  </Link>
                )}
                {task.project != null && (
                  <Link
                    className="text-primary hover:underline"
                    to={`/projects/${task.project}`}
                  >
                    Проект #{task.project}
                  </Link>
                )}
                {task.wbs_node != null && (
                  <span className="text-text-muted">
                    WBS {task.wbs_code || `#${task.wbs_node}`}
                    {task.wbs_title ? ` · ${task.wbs_title}` : ""}
                  </span>
                )}
              </div>
              {task.project != null && (
                <div className="mt-2">
                  <label className="block text-xs text-text-muted">
                    Привязка к WBS
                    <select
                      className="mt-1 w-full max-w-md rounded-lg border border-border bg-cream px-3 py-2 text-sm"
                      value={task.wbs_node ?? ""}
                      onChange={(e) => {
                        const raw = e.target.value;
                        void bind(task, raw ? Number(raw) : null);
                      }}
                    >
                      <option value="">Без привязки</option>
                      {flat.map((node) => (
                        <option key={node.id} value={node.id}>
                          {" ".repeat(node.depth)}
                          {node.code} · {node.title}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>
              )}
              {Object.keys(task.form_schema || {}).length > 0 && (
                <pre className="mt-2 overflow-x-auto rounded bg-cream p-2 text-xs">
                  {JSON.stringify(task.form_schema, null, 2)}
                </pre>
              )}
              <div className="mt-3 flex flex-wrap items-end gap-2">
                <input
                  className="min-w-[12rem] flex-1 rounded-lg border border-border bg-cream px-3 py-2 text-sm"
                  placeholder="Комментарий"
                  value={notes[task.id] || ""}
                  onChange={(e) =>
                    setNotes((prev) => ({ ...prev, [task.id]: e.target.value }))
                  }
                />
                <button
                  type="button"
                  className="rounded-lg bg-primary px-3 py-2 text-sm font-semibold text-white"
                  onClick={() => void complete(task, true)}
                >
                  Одобрить
                </button>
                <button
                  type="button"
                  className="rounded-lg border border-border px-3 py-2 text-sm"
                  onClick={() => void complete(task, false)}
                >
                  Отклонить
                </button>
              </div>
            </li>
          );
        })}
        {!loading && tasks.length === 0 && (
          <li className="text-sm text-text-muted">Нет открытых задач</li>
        )}
      </ul>
    </div>
  );
}
