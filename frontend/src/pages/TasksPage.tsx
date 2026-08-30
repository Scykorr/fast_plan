import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { parseApiError } from "../api/errors";
import type { Project } from "../api/projects";
import type { IssueStatus } from "../api/tracking";
import type { WorkspaceMember, WorkspaceTask } from "../api/workspace";
import { ErrorMessage } from "../components/ErrorMessage";
import { useAuth } from "../context/AuthContext";
import { useWorkspace } from "../context/WorkspaceContext";
import { useProjectsApi } from "../hooks/useProjectsApi";
import { useTrackingApi } from "../hooks/useTrackingApi";
import { useWorkspaceApi } from "../hooks/useWorkspaceApi";

type SortField =
  | "code"
  | "title"
  | "project"
  | "assignee"
  | "status"
  | "progress"
  | "start_date"
  | "end_date"
  | "days_overdue";

type ColumnId =
  | "code"
  | "title"
  | "project"
  | "assignee"
  | "status"
  | "progress"
  | "start_date"
  | "end_date"
  | "overdue";

const COLUMNS: Array<{
  id: ColumnId;
  label: string;
  sort?: SortField;
  defaultVisible: boolean;
}> = [
  { id: "code", label: "Ключ", sort: "code", defaultVisible: true },
  { id: "title", label: "Тема", sort: "title", defaultVisible: true },
  { id: "project", label: "Проект", sort: "project", defaultVisible: true },
  { id: "assignee", label: "Исполнитель", sort: "assignee", defaultVisible: true },
  { id: "status", label: "Статус", sort: "status", defaultVisible: true },
  { id: "progress", label: "Прогресс", sort: "progress", defaultVisible: true },
  { id: "start_date", label: "Начало", sort: "start_date", defaultVisible: false },
  { id: "end_date", label: "Срок", sort: "end_date", defaultVisible: true },
  { id: "overdue", label: "Просрочка", sort: "days_overdue", defaultVisible: false },
];

function renderCell(column: ColumnId, task: WorkspaceTask) {
  switch (column) {
    case "code":
      return <span className="font-mono text-xs">{task.wbs_code}</span>;
    case "title":
      return <span className="font-medium text-text">{task.title}</span>;
    case "project":
      return task.project_name;
    case "assignee":
      return task.assignee_name ?? "—";
    case "status":
      return task.workflow_status_name ?? "—";
    case "progress":
      return `${task.progress}%`;
    case "start_date":
      return task.start_date ?? "—";
    case "end_date":
      return task.end_date ?? "—";
    case "overdue":
      return task.days_overdue > 0 ? (
        <span className="font-medium text-primary">+{task.days_overdue} дн.</span>
      ) : (
        "—"
      );
    default:
      return null;
  }
}

export function TasksPage() {
  const { user } = useAuth();
  const workspaceApi = useWorkspaceApi();
  const projectsApi = useProjectsApi();
  const trackingApi = useTrackingApi();
  const { workspaceEpoch, activeWorkspace } = useWorkspace();

  const [tasks, setTasks] = useState<WorkspaceTask[]>([]);
  const [summary, setSummary] = useState({
    total: 0,
    overdue: 0,
    due_soon: 0,
    returned: 0,
  });
  const [projects, setProjects] = useState<Project[]>([]);
  const [members, setMembers] = useState<WorkspaceMember[]>([]);
  const [statuses, setStatuses] = useState<IssueStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [projectId, setProjectId] = useState<number | "">("");
  const [assigneeFilter, setAssigneeFilter] = useState<
    "all" | "me" | "unassigned" | number
  >("all");
  const [statusId, setStatusId] = useState<number | "">("");
  const [search, setSearch] = useState("");
  const [includeDone, setIncludeDone] = useState(false);
  const [overdueOnly, setOverdueOnly] = useState(false);
  const [sort, setSort] = useState<{ field: SortField; order: "asc" | "desc" }>({
    field: "end_date",
    order: "asc",
  });
  const [visibleColumns, setVisibleColumns] = useState<Set<ColumnId>>(
    () => new Set(COLUMNS.filter((c) => c.defaultVisible).map((c) => c.id)),
  );
  const [columnsOpen, setColumnsOpen] = useState(false);
  const [selectedId, setSelectedId] = useState<number | null>(null);

  const selectedTask = useMemo(
    () => tasks.find((task) => task.wbs_id === selectedId) ?? null,
    [tasks, selectedId],
  );

  const visibleColumnList = useMemo(
    () => COLUMNS.filter((column) => visibleColumns.has(column.id)),
    [visibleColumns],
  );

  useEffect(() => {
    if (!projectsApi || !workspaceApi || !trackingApi) {
      return;
    }
    void Promise.all([
      projectsApi.getProjects(),
      workspaceApi.getMembers(),
      trackingApi.getMetadata(),
    ])
      .then(([projectRows, memberRows, metadata]) => {
        setProjects(projectRows);
        setMembers(memberRows);
        setStatuses(metadata.statuses);
      })
      .catch(() => undefined);
  }, [projectsApi, workspaceApi, trackingApi, workspaceEpoch]);

  const load = useCallback(async () => {
    if (!workspaceApi) {
      return;
    }
    setLoading(true);
    setError("");
    try {
      const data = await workspaceApi.getTasks({
        project: projectId === "" ? undefined : projectId,
        assignee:
          assigneeFilter === "all"
            ? "all"
            : assigneeFilter === "me"
              ? "me"
              : assigneeFilter === "unassigned"
                ? undefined
                : assigneeFilter,
        unassigned: assigneeFilter === "unassigned",
        status: statusId === "" ? undefined : statusId,
        q: search,
        include_done: includeDone,
        overdue_only: overdueOnly,
        sort: sort.field,
        order: sort.order,
        limit: 200,
      });
      setTasks(data.tasks);
      setSummary(data.summary);
      if (
        selectedId != null &&
        !data.tasks.some((task) => task.wbs_id === selectedId)
      ) {
        setSelectedId(null);
      }
    } catch (err) {
      setError(parseApiError(err, "Не удалось загрузить задачи"));
    } finally {
      setLoading(false);
    }
  }, [
    workspaceApi,
    projectId,
    assigneeFilter,
    statusId,
    search,
    includeDone,
    overdueOnly,
    sort,
    selectedId,
  ]);

  useEffect(() => {
    void load();
  }, [load, workspaceEpoch, activeWorkspace?.id]);

  const toggleSort = (field: SortField) => {
    setSort((current) =>
      current.field === field
        ? { field, order: current.order === "asc" ? "desc" : "asc" }
        : { field, order: "asc" },
    );
  };

  const toggleColumn = (id: ColumnId) => {
    setVisibleColumns((current) => {
      const next = new Set(current);
      if (next.has(id)) {
        if (next.size > 1) {
          next.delete(id);
        }
      } else {
        next.add(id);
      }
      return next;
    });
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-3xl font-bold text-text">Задачи</h1>
          <p className="mt-1 text-sm text-text-muted">
            Найдено: {summary.total}
            {summary.returned < summary.total
              ? ` · показано ${summary.returned}`
              : ""}
            · просрочено: {summary.overdue} · скоро: {summary.due_soon}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <div className="relative">
            <button
              type="button"
              onClick={() => setColumnsOpen((open) => !open)}
              className="rounded-lg border border-border px-3 py-1.5 text-xs font-medium text-text"
            >
              Столбцы
            </button>
            {columnsOpen && (
              <div className="absolute right-0 z-20 mt-1 w-52 rounded-xl border border-border bg-surface p-3 shadow-lg">
                <p className="mb-2 text-xs font-semibold text-text">Столбцы</p>
                <ul className="space-y-1 text-sm">
                  {COLUMNS.map((column) => (
                    <li key={column.id}>
                      <label className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          checked={visibleColumns.has(column.id)}
                          onChange={() => toggleColumn(column.id)}
                        />
                        {column.label}
                      </label>
                    </li>
                  ))}
                </ul>
                <button
                  type="button"
                  onClick={() => setColumnsOpen(false)}
                  className="mt-3 w-full rounded-lg bg-primary px-2 py-1 text-xs text-white"
                >
                  Готово
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      <ErrorMessage message={error} onDismiss={() => setError("")} />

      <div className="flex flex-wrap items-end gap-3 rounded-xl border border-border bg-surface p-4">
        <label className="text-sm">
          <span className="mb-1 block text-text-muted">Проект</span>
          <select
            value={projectId}
            onChange={(event) =>
              setProjectId(event.target.value ? Number(event.target.value) : "")
            }
            className="min-w-[10rem] rounded-lg border border-border bg-cream px-3 py-2"
          >
            <option value="">Все проекты</option>
            {projects.map((project) => (
              <option key={project.id} value={project.id}>
                {project.name}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          <span className="mb-1 block text-text-muted">Исполнитель</span>
          <select
            value={
              assigneeFilter === "all"
                ? "all"
                : assigneeFilter === "me"
                  ? "me"
                  : assigneeFilter === "unassigned"
                    ? "unassigned"
                    : String(assigneeFilter)
            }
            onChange={(event) => {
              const value = event.target.value;
              if (value === "all" || value === "me" || value === "unassigned") {
                setAssigneeFilter(value);
                return;
              }
              setAssigneeFilter(Number(value));
            }}
            className="min-w-[10rem] rounded-lg border border-border bg-cream px-3 py-2"
          >
            <option value="all">Все исполнители</option>
            <option value="me">Назначено мне</option>
            <option value="unassigned">Без исполнителя</option>
            {members.map((member) => (
              <option key={member.user_id} value={member.user_id}>
                {member.username || member.email}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          <span className="mb-1 block text-text-muted">Статус</span>
          <select
            value={statusId}
            onChange={(event) =>
              setStatusId(event.target.value ? Number(event.target.value) : "")
            }
            className="min-w-[10rem] rounded-lg border border-border bg-cream px-3 py-2"
          >
            <option value="">Все статусы</option>
            {statuses.map((status) => (
              <option key={status.id} value={status.id}>
                {status.name}
              </option>
            ))}
          </select>
        </label>
        <label className="min-w-[12rem] flex-1 text-sm">
          <span className="mb-1 block text-text-muted">Поиск</span>
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Ключ или тема…"
            className="w-full rounded-lg border border-border bg-cream px-3 py-2"
          />
        </label>
        <label className="flex items-center gap-2 text-sm text-text">
          <input
            type="checkbox"
            checked={overdueOnly}
            onChange={(event) => setOverdueOnly(event.target.checked)}
          />
          Только просроченные
        </label>
        <label className="flex items-center gap-2 text-sm text-text">
          <input
            type="checkbox"
            checked={includeDone}
            onChange={(event) => setIncludeDone(event.target.checked)}
          />
          Включая завершённые
        </label>
      </div>

      {loading && <p className="text-sm text-text-muted">Загрузка…</p>}

      {!loading && tasks.length === 0 && (
        <p className="text-sm text-text-muted">Задач не найдено</p>
      )}

      <div
        className={[
          selectedTask
            ? "grid items-start gap-4 lg:grid-cols-[minmax(0,1.4fr)_minmax(18rem,1fr)]"
            : "",
        ].join(" ")}
      >
        {tasks.length > 0 && (
          <div className="overflow-x-auto rounded-xl border border-border bg-surface">
            <table className="min-w-full text-left text-sm">
              <thead className="border-b border-border bg-cream/60 text-xs uppercase tracking-wide text-text-muted">
                <tr>
                  {visibleColumnList.map((column) => (
                    <th key={column.id} className="px-3 py-2 font-medium">
                      {column.sort ? (
                        <button
                          type="button"
                          onClick={() => toggleSort(column.sort!)}
                          className="inline-flex items-center gap-1 hover:text-text"
                        >
                          {column.label}
                          {sort.field === column.sort && (
                            <span>{sort.order === "asc" ? "↑" : "↓"}</span>
                          )}
                        </button>
                      ) : (
                        column.label
                      )}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {tasks.map((task) => (
                  <tr
                    key={task.wbs_id}
                    onClick={() => setSelectedId(task.wbs_id)}
                    className={[
                      "cursor-pointer border-b border-border/60 hover:bg-cream/40",
                      selectedId === task.wbs_id ? "bg-cream/70" : "",
                    ].join(" ")}
                  >
                    {visibleColumnList.map((column) => (
                      <td key={column.id} className="px-3 py-2 text-text-muted">
                        {renderCell(column.id, task)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {selectedTask && (
          <aside className="rounded-xl border border-border bg-surface p-4 lg:sticky lg:top-4">
            <div className="flex items-start justify-between gap-2">
              <p className="font-mono text-xs text-text-muted">{selectedTask.wbs_code}</p>
              <button
                type="button"
                onClick={() => setSelectedId(null)}
                className="rounded-lg px-2 py-1 text-xs text-text-muted hover:bg-cream hover:text-text"
                aria-label="Закрыть карточку"
              >
                ×
              </button>
            </div>
            <h2 className="mt-1 text-lg font-semibold text-text">{selectedTask.title}</h2>
            <dl className="mt-4 space-y-2 text-sm">
              <div>
                <dt className="text-text-muted">Проект</dt>
                <dd>{selectedTask.project_name}</dd>
              </div>
              <div>
                <dt className="text-text-muted">Исполнитель</dt>
                <dd>{selectedTask.assignee_name ?? "—"}</dd>
              </div>
              <div>
                <dt className="text-text-muted">Статус</dt>
                <dd>{selectedTask.workflow_status_name ?? "—"}</dd>
              </div>
              <div>
                <dt className="text-text-muted">Прогресс</dt>
                <dd>{selectedTask.progress}%</dd>
              </div>
              {selectedTask.start_date && (
                <div>
                  <dt className="text-text-muted">Начало</dt>
                  <dd>{selectedTask.start_date}</dd>
                </div>
              )}
              {selectedTask.end_date && (
                <div>
                  <dt className="text-text-muted">Срок</dt>
                  <dd>{selectedTask.end_date}</dd>
                </div>
              )}
              {selectedTask.days_overdue > 0 && (
                <div>
                  <dt className="text-text-muted">Просрочка</dt>
                  <dd className="font-medium text-primary">
                    +{selectedTask.days_overdue} дн.
                  </dd>
                </div>
              )}
              {selectedTask.description && (
                <div>
                  <dt className="text-text-muted">Описание</dt>
                  <dd className="whitespace-pre-wrap">{selectedTask.description}</dd>
                </div>
              )}
            </dl>
            <Link
              to={selectedTask.link}
              className="mt-4 inline-block rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white"
            >
              Открыть в проекте
            </Link>
          </aside>
        )}
      </div>

      {user && assigneeFilter === "me" && (
        <p className="text-xs text-text-muted">
          Фильтр «Назначено мне» для {user.email}
        </p>
      )}
    </div>
  );
}
