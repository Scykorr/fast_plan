import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { parseApiError } from "../api/errors";
import type { DeliveryTask } from "../api/delivery";
import type { MyTask } from "../api/workspace";
import { ErrorMessage } from "../components/ErrorMessage";
import { useDeliveryApi } from "../hooks/useDeliveryApi";
import { useWorkspace } from "../context/WorkspaceContext";
import { useWorkspaceApi } from "../hooks/useWorkspaceApi";

const BUCKETS: Array<{
  key:
    | "new_assignments"
    | "in_progress"
    | "waiting_response"
    | "returned_for_rework";
  title: string;
}> = [
  { key: "new_assignments", title: "Новые назначения" },
  { key: "in_progress", title: "В работе" },
  { key: "waiting_response", title: "Ожидают вашего ответа" },
  { key: "returned_for_rework", title: "Возвращены на доработку" },
];

export function MyTasksPage() {
  const workspaceApi = useWorkspaceApi();
  const deliveryApi = useDeliveryApi();
  const { workspaceEpoch, activeWorkspace } = useWorkspace();
  const [tasks, setTasks] = useState<MyTask[]>([]);
  const [summary, setSummary] = useState({ total: 0, overdue: 0, due_soon: 0 });
  const [deliveryBuckets, setDeliveryBuckets] = useState<{
    new_assignments: DeliveryTask[];
    in_progress: DeliveryTask[];
    waiting_response: DeliveryTask[];
    returned_for_rework: DeliveryTask[];
    blocked: DeliveryTask[];
    total: number;
  } | null>(null);
  const [overdueOnly, setOverdueOnly] = useState(false);
  const [includeDone, setIncludeDone] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    if (!workspaceApi) {
      return;
    }
    setLoading(true);
    setError("");
    try {
      const data = await workspaceApi.getMyTasks({
        overdue_only: overdueOnly || undefined,
        include_done: includeDone || undefined,
      });
      setTasks(data.tasks);
      setSummary(data.summary);
      if (deliveryApi) {
        try {
          setDeliveryBuckets(await deliveryApi.getMyTasks());
        } catch {
          setDeliveryBuckets(null);
        }
      }
    } catch (err) {
      setError(parseApiError(err, "Не удалось загрузить задачи"));
    } finally {
      setLoading(false);
    }
  }, [workspaceApi, deliveryApi, overdueOnly, includeDone]);

  useEffect(() => {
    void load();
  }, [load, workspaceEpoch, activeWorkspace?.id]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-text">Мои задачи</h1>
        <p className="mt-2 text-text-muted">
          WBS: {summary.total} · Просрочено: {summary.overdue} · Скоро:{" "}
          {summary.due_soon}
          {deliveryBuckets
            ? ` · Agent Ops: ${deliveryBuckets.total}`
            : ""}
        </p>
      </div>

      <ErrorMessage message={error} onDismiss={() => setError("")} />

      {deliveryBuckets && deliveryBuckets.total > 0 && (
        <section className="space-y-4">
          <h2 className="text-lg font-semibold text-text">Agent Ops</h2>
          {BUCKETS.map((bucket) => {
            const items = deliveryBuckets[bucket.key];
            if (!items.length) {
              return null;
            }
            return (
              <div key={bucket.key}>
                <h3 className="mb-2 text-sm font-medium text-text-muted">
                  {bucket.title}
                </h3>
                <ul className="space-y-2">
                  {items.map((task) => (
                    <li key={task.id}>
                      <Link
                        to={`/agent-ops?task=${task.id}`}
                        className="block rounded-xl border border-border bg-surface px-4 py-3 hover:bg-cream"
                      >
                        <p className="text-sm font-medium text-text">
                          #{task.id} {task.title}
                        </p>
                        <p className="text-xs text-text-muted">
                          {task.status_label || task.status}
                          {task.epic_title ? ` · эпик: ${task.epic_title}` : ""}
                          {task.assignee_role
                            ? ` · роль: ${task.assignee_role}`
                            : ""}
                        </p>
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            );
          })}
        </section>
      )}

      <div className="flex flex-wrap gap-4">
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

      {loading && <p className="text-sm text-text-muted">Загрузка...</p>}

      {!loading && tasks.length === 0 && (
        <p className="text-sm text-text-muted">WBS-задач нет</p>
      )}

      <ul className="space-y-2">
        {tasks.map((task) => (
          <li key={task.wbs_id}>
            <Link
              to={task.link}
              className="block rounded-xl border border-border bg-surface px-4 py-3 hover:bg-cream"
            >
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <p className="text-sm font-medium text-text">
                    {task.wbs_code} {task.title}
                  </p>
                  <p className="text-xs text-text-muted">
                    {task.project_name}
                    {task.workflow_status_name
                      ? ` · ${task.workflow_status_name}`
                      : ""}
                  </p>
                </div>
                <div className="text-right text-xs text-text-muted">
                  <p>{task.progress}%</p>
                  {task.days_overdue > 0 && (
                    <p className="font-medium text-primary">
                      +{task.days_overdue} дн.
                    </p>
                  )}
                  {task.end_date && <p>до {task.end_date}</p>}
                </div>
              </div>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
