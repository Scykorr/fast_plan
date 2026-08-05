import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { parseApiError } from "../api/errors";
import type { ProcessUserTask } from "../api/process";
import type { WBSNode } from "../api/projects";
import type { WorkspaceMember } from "../api/workspace";
import { AssigneeSelect } from "../components/AssigneeSelect";
import { ErrorMessage } from "../components/ErrorMessage";
import { useProcessApi } from "../hooks/useProcessApi";
import { useProjectsApi } from "../hooks/useProjectsApi";
import { useWorkspaceApi } from "../hooks/useWorkspaceApi";
import { useWorkspace } from "../context/WorkspaceContext";
import { getSlaInfo, slaBadgeClass } from "../utils/sla";

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

type SlaFilter = "all" | "overdue" | "soon" | "ok";

export function ProcessTasksPage() {
  const api = useProcessApi();
  const projectsApi = useProjectsApi();
  const workspaceApi = useWorkspaceApi();
  const { workspaceEpoch } = useWorkspace();
  const [searchParams, setSearchParams] = useSearchParams();
  const [tasks, setTasks] = useState<ProcessUserTask[]>([]);
  const [members, setMembers] = useState<WorkspaceMember[]>([]);
  const [wbsByProject, setWbsByProject] = useState<Record<number, WBSNode[]>>({});
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [notes, setNotes] = useState<Record<number, string>>({});
  const [loading, setLoading] = useState(false);
  const [now, setNow] = useState(() => new Date());
  const highlightId = Number(searchParams.get("task") || "") || null;
  const slaFilter = (searchParams.get("sla") as SlaFilter) || "all";

  useEffect(() => {
    const id = window.setInterval(() => setNow(new Date()), 60_000);
    return () => window.clearInterval(id);
  }, []);

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
              next[projectId] = await projectsApi.getWBS(projectId);
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

  useEffect(() => {
    if (!workspaceApi) return;
    void workspaceApi.getMembers().then(setMembers).catch(() => undefined);
  }, [workspaceApi, workspaceEpoch]);

  const assign = async (task: ProcessUserTask, assigneeId: number | null) => {
    if (!api) return;
    try {
      const updated = await api.assignTask(task.id, assigneeId);
      setTasks((prev) => prev.map((t) => (t.id === task.id ? updated : t)));
      setMessage(`Задача #${task.id}: исполнитель обновлён`);
    } catch (err) {
      setError(parseApiError(err));
    }
  };

  const sortedFiltered = useMemo(() => {
    const withSla = tasks.map((task) => ({
      task,
      sla: getSlaInfo(task.due_at, now),
    }));
    const filtered =
      slaFilter === "all"
        ? withSla
        : withSla.filter(({ sla }) => sla.state === slaFilter);
    const rank = { overdue: 0, soon: 1, ok: 2, none: 3 } as const;
    return filtered.sort((a, b) => {
      const ra = rank[a.sla.state];
      const rb = rank[b.sla.state];
      if (ra !== rb) return ra - rb;
      const ma = a.sla.msRemaining;
      const mb = b.sla.msRemaining;
      if (ma == null && mb == null) return b.task.id - a.task.id;
      if (ma == null) return 1;
      if (mb == null) return -1;
      return ma - mb;
    });
  }, [tasks, now, slaFilter]);

  const setSlaFilter = (next: SlaFilter) => {
    const params = new URLSearchParams(searchParams);
    if (next === "all") params.delete("sla");
    else params.set("sla", next);
    setSearchParams(params, { replace: true });
  };

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

  const filters: { id: SlaFilter; label: string }[] = [
    { id: "all", label: "Все" },
    { id: "overdue", label: "Просрочено" },
    { id: "soon", label: "Скоро" },
    { id: "ok", label: "В срок" },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-text">Задачи процессов</h1>
          <p className="mt-1 text-sm text-text-muted">
            Inbox user tasks (BPMN). SLA по due_at; привязка к WBS синхронизирует
            прогресс и Kanban при завершении.
          </p>
        </div>
        <Link to="/processes?tab=ops" className="text-sm text-primary hover:underline">
          Ops / SLA board →
        </Link>
      </div>
      <div className="flex flex-wrap gap-2">
        {filters.map((f) => (
          <button
            key={f.id}
            type="button"
            onClick={() => setSlaFilter(f.id)}
            className={[
              "rounded-lg border px-3 py-1.5 text-xs font-medium",
              slaFilter === f.id
                ? "border-primary bg-primary/10 text-primary"
                : "border-border text-text-muted hover:text-text",
            ].join(" ")}
          >
            {f.label}
          </button>
        ))}
      </div>
      <ErrorMessage message={error} />
      {message && (
        <p className="text-sm text-secondary" role="status">
          {message}
        </p>
      )}
      {loading && <p className="text-sm text-text-muted">Загрузка…</p>}
      <ul className="space-y-3">
        {sortedFiltered.map(({ task, sla }) => {
          const flat =
            task.project != null
              ? flattenWbs(wbsByProject[task.project] || [])
              : [];
          const highlighted = highlightId === task.id;
          return (
            <li
              key={task.id}
              id={`task-${task.id}`}
              className={[
                "rounded-xl border bg-surface p-4",
                highlighted
                  ? "border-primary ring-2 ring-primary/30"
                  : "border-border",
              ].join(" ")}
            >
              <div className="flex flex-wrap items-start justify-between gap-2">
                <p className="font-semibold text-text">{task.name}</p>
                <span
                  className={[
                    "rounded-md border px-2 py-0.5 text-xs font-medium",
                    slaBadgeClass(sla.state),
                  ].join(" ")}
                  title={
                    task.due_at
                      ? new Date(task.due_at).toLocaleString()
                      : undefined
                  }
                >
                  {sla.label}
                </span>
              </div>
              <p className="text-xs text-text-muted">
                {task.definition_name} · instance #{task.instance_id}
                {task.due_at
                  ? ` · due ${new Date(task.due_at).toLocaleString()}`
                  : ""}
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
              <div className="mt-2 max-w-md">
                <label className="block text-xs text-text-muted">
                  Исполнитель
                  <AssigneeSelect
                    members={members}
                    value={task.assignee}
                    onChange={(id) => void assign(task, id)}
                    className="mt-1 w-full rounded-lg border border-border bg-cream px-3 py-2 text-sm"
                    emptyLabel="Не назначен"
                  />
                </label>
              </div>
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
        {!loading && sortedFiltered.length === 0 && (
          <li className="text-sm text-text-muted">Нет открытых задач</li>
        )}
      </ul>
    </div>
  );
}
