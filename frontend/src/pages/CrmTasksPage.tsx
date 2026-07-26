import {
  DndContext,
  PointerSensor,
  closestCorners,
  useDroppable,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { parseApiError } from "../api/errors";
import type {
  CrmBoardTask,
  CrmTaskBoardStatus,
  CrmTaskPriority,
} from "../api/crm";
import { ErrorMessage } from "../components/ErrorMessage";
import { useCrmApi } from "../hooks/useCrmApi";
import { useWorkspace } from "../context/WorkspaceContext";

const COLUMNS: Array<{ id: CrmTaskBoardStatus; label: string }> = [
  { id: "todo", label: "К выполнению" },
  { id: "doing", label: "В работе" },
  { id: "done", label: "Готово" },
];

const PRIORITY_LABEL: Record<CrmTaskPriority, string> = {
  low: "низкий",
  normal: "обычный",
  high: "высокий",
  urgent: "срочный",
};

function TaskCard({ task }: { task: CrmBoardTask }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({
      id: `${task.kind}-${task.id}`,
      data: { task },
    });
  const checklistDone = task.checklist.filter((item) => item.done).length;
  const checklistTotal = task.checklist.length;
  const parent =
    task.kind === "deal"
      ? { to: `/deals?deal=${task.deal_id}`, label: task.deal_title || "Сделка" }
      : { to: `/leads`, label: task.lead_name || "Лид" };

  return (
    <article
      ref={setNodeRef}
      style={{
        transform: CSS.Transform.toString(transform),
        transition,
        opacity: isDragging ? 0.5 : 1,
      }}
      className="rounded-lg border border-border bg-surface px-2.5 py-2 text-sm shadow-sm"
      {...attributes}
      {...listeners}
    >
      <div className="flex items-start justify-between gap-2">
        <p className="font-medium text-text">{task.title}</p>
        <span className="shrink-0 rounded bg-cream px-1.5 py-0.5 text-[10px] uppercase text-text-muted">
          {task.kind === "deal" ? "сделка" : "лид"}
        </span>
      </div>
      <p className="mt-1 text-[11px] text-text-muted">
        <Link to={parent.to} className="text-primary hover:underline">
          {parent.label}
        </Link>
        {task.due_date ? ` · до ${task.due_date}` : ""}
        {task.repeat !== "none" ? ` · ${task.repeat}` : ""}
      </p>
      <div className="mt-1.5 flex flex-wrap gap-1 text-[10px] text-text-muted">
        <span className="rounded border border-border px-1.5 py-0.5">
          {PRIORITY_LABEL[task.priority]}
        </span>
        {checklistTotal > 0 && (
          <span className="rounded border border-border px-1.5 py-0.5">
            ✓ {checklistDone}/{checklistTotal}
          </span>
        )}
      </div>
    </article>
  );
}

function Column({
  status,
  label,
  tasks,
}: {
  status: CrmTaskBoardStatus;
  label: string;
  tasks: CrmBoardTask[];
}) {
  const { setNodeRef, isOver } = useDroppable({ id: status });
  return (
    <section
      ref={setNodeRef}
      className={[
        "flex min-h-[18rem] flex-1 flex-col rounded-xl border border-border bg-cream/40 p-2",
        isOver ? "border-primary" : "",
      ].join(" ")}
    >
      <h2 className="mb-2 px-1 text-xs font-semibold uppercase tracking-wide text-text-muted">
        {label} · {tasks.length}
      </h2>
      <SortableContext
        items={tasks.map((task) => `${task.kind}-${task.id}`)}
        strategy={verticalListSortingStrategy}
      >
        <div className="flex flex-1 flex-col gap-2">
          {tasks.map((task) => (
            <TaskCard key={`${task.kind}-${task.id}`} task={task} />
          ))}
        </div>
      </SortableContext>
    </section>
  );
}

export function CrmTasksPage() {
  const crmApi = useCrmApi();
  const { workspaceEpoch, activeWorkspace } = useWorkspace();
  const [tasks, setTasks] = useState<CrmBoardTask[]>([]);
  const [includeDone, setIncludeDone] = useState(true);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
  );

  const load = useCallback(async () => {
    if (!crmApi) {
      return;
    }
    setLoading(true);
    setError("");
    try {
      const data = await crmApi.listCrmTaskBoard({ include_done: includeDone });
      setTasks(data.results);
    } catch (err) {
      setError(parseApiError(err, "Не удалось загрузить CRM-задачи"));
    } finally {
      setLoading(false);
    }
  }, [crmApi, includeDone]);

  useEffect(() => {
    void load();
  }, [load, workspaceEpoch, activeWorkspace?.id]);

  const byStatus = useMemo(() => {
    const map: Record<CrmTaskBoardStatus, CrmBoardTask[]> = {
      todo: [],
      doing: [],
      done: [],
    };
    for (const task of tasks) {
      map[task.board_status]?.push(task);
    }
    return map;
  }, [tasks]);

  const onDragEnd = async (event: DragEndEvent) => {
    const activeId = String(event.active.id);
    const overId = event.over?.id ? String(event.over.id) : "";
    if (!crmApi || !overId) {
      return;
    }
    const [kind, idRaw] = activeId.split("-");
    const taskId = Number(idRaw);
    if ((kind !== "deal" && kind !== "lead") || !taskId) {
      return;
    }
    let nextStatus: CrmTaskBoardStatus | null = null;
    if (overId === "todo" || overId === "doing" || overId === "done") {
      nextStatus = overId;
    } else if (overId.includes("-")) {
      const overTask = tasks.find((task) => `${task.kind}-${task.id}` === overId);
      nextStatus = overTask?.board_status ?? null;
    }
    const current = tasks.find((task) => task.kind === kind && task.id === taskId);
    if (!nextStatus || !current || current.board_status === nextStatus) {
      return;
    }
    setTasks((prev) =>
      prev.map((task) =>
        task.kind === kind && task.id === taskId
          ? {
              ...task,
              board_status: nextStatus,
              is_done: nextStatus === "done",
            }
          : task,
      ),
    );
    try {
      await crmApi.moveCrmBoardTask(kind, taskId, nextStatus);
      await load();
    } catch (err) {
      setError(parseApiError(err, "Не удалось переместить задачу"));
      await load();
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-text">CRM задачидачи</h1>
          <p className="mt-1 text-sm text-text-muted">
            Единый Kanban по сделкам и лидам · priority · checklist · repeat
          </p>
        </div>
        <label className="flex items-center gap-2 text-sm text-text">
          <input
            type="checkbox"
            checked={includeDone}
            onChange={(event) => setIncludeDone(event.target.checked)}
          />
          Показывать готовые
        </label>
      </div>

      {error && <ErrorMessage message={error} onDismiss={() => setError("")} />}
      {loading && <p className="text-sm text-text-muted">Загрузка…</p>}

      {!loading && (
        <DndContext
          sensors={sensors}
          collisionDetection={closestCorners}
          onDragEnd={(event) => void onDragEnd(event)}
        >
          <div className="flex flex-col gap-3 lg:flex-row">
            {COLUMNS.map((column) => (
              <Column
                key={column.id}
                status={column.id}
                label={column.label}
                tasks={byStatus[column.id]}
              />
            ))}
          </div>
        </DndContext>
      )}
    </div>
  );
}
