import {
  DndContext,
  DragOverlay,
  PointerSensor,
  closestCorners,
  useDroppable,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  arrayMove,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import { useSearchParams } from "react-router-dom";

import { parseApiError } from "../api/errors";
import type {
  CrmDeal,
  CrmDealForecast,
  CrmDealTask,
  CrmOrganization,
  CrmPipeline,
  CrmPipelineStage,
} from "../api/crm";
import type { Project } from "../api/projects";
import { ErrorMessage } from "../components/ErrorMessage";
import { useCrmApi } from "../hooks/useCrmApi";
import { useProjectsApi } from "../hooks/useProjectsApi";
import { useWorkspace } from "../context/WorkspaceContext";

function money(value: string | number | undefined) {
  const n = typeof value === "string" ? Number(value) : value ?? 0;
  return n.toLocaleString("ru-RU", { maximumFractionDigits: 0 });
}

function DealCard({
  deal,
  selected,
  onSelect,
}: {
  deal: CrmDeal;
  selected: boolean;
  onSelect: () => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({
      id: `deal-${deal.id}`,
      data: { type: "deal", deal },
    });

  return (
    <button
      type="button"
      ref={setNodeRef}
      style={{
        transform: CSS.Transform.toString(transform),
        transition,
        opacity: isDragging ? 0.4 : 1,
      }}
      {...attributes}
      {...listeners}
      onClick={onSelect}
      className={`w-full cursor-grab rounded-lg border px-3 py-2 text-left text-sm active:cursor-grabbing ${
        selected
          ? "border-primary bg-cream"
          : "border-border bg-cream/40 hover:border-primary/50"
      }`}
    >
      <p className="font-medium text-text">{deal.title}</p>
      <p className="text-xs text-text-muted">
        {money(deal.amount)} · {deal.probability}%
        {deal.organization_name ? ` · ${deal.organization_name}` : ""}
        {deal.project_name ? ` · ${deal.project_name}` : ""}
      </p>
      {(deal.open_tasks_count ?? 0) > 0 && (
        <p className="mt-1 text-[10px] text-amber-700 dark:text-amber-300">
          Задач: {deal.open_tasks_count}
        </p>
      )}
    </button>
  );
}

function StageColumn({
  stage,
  deals,
  selectedId,
  onSelect,
}: {
  stage: CrmPipelineStage;
  deals: CrmDeal[];
  selectedId: number | null;
  onSelect: (deal: CrmDeal) => void;
}) {
  const { setNodeRef, isOver } = useDroppable({
    id: `stage-${stage.id}`,
    data: { type: "stage", stage },
  });
  const ids = deals.map((deal) => `deal-${deal.id}`);

  return (
    <div
      ref={setNodeRef}
      className={`w-64 shrink-0 rounded-xl border bg-surface ${
        isOver ? "border-primary" : "border-border"
      }`}
    >
      <div className="border-b border-border px-3 py-2">
        <p className="text-sm font-semibold text-text">{stage.name}</p>
        <p className="text-xs text-text-muted">
          {stage.default_probability}% · {deals.length}
        </p>
      </div>
      <SortableContext items={ids} strategy={verticalListSortingStrategy}>
        <ul className="max-h-[28rem] space-y-2 overflow-y-auto p-2">
          {deals.length === 0 && (
            <li className="px-2 py-6 text-center text-xs text-text-muted">
              Перетащите сюда
            </li>
          )}
          {deals.map((deal) => (
            <li key={deal.id}>
              <DealCard
                deal={deal}
                selected={selectedId === deal.id}
                onSelect={() => onSelect(deal)}
              />
            </li>
          ))}
        </ul>
      </SortableContext>
    </div>
  );
}

export function DealsPage() {
  const crmApi = useCrmApi();
  const projectsApi = useProjectsApi();
  const { workspaceEpoch } = useWorkspace();
  const [searchParams, setSearchParams] = useSearchParams();
  const dealFromQuery = Number(searchParams.get("deal") || 0) || null;
  const [pipeline, setPipeline] = useState<CrmPipeline | null>(null);
  const [deals, setDeals] = useState<CrmDeal[]>([]);
  const [orgs, setOrgs] = useState<CrmOrganization[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [forecast, setForecast] = useState<CrmDealForecast | null>(null);
  const [selected, setSelected] = useState<CrmDeal | null>(null);
  const [tasks, setTasks] = useState<CrmDealTask[]>([]);
  const [activeDeal, setActiveDeal] = useState<CrmDeal | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({
    title: "",
    amount: "",
    organization_id: "" as number | "",
    close_date: "",
  });
  const [taskTitle, setTaskTitle] = useState("");
  const [taskDue, setTaskDue] = useState("");

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
  );

  const load = useCallback(async () => {
    if (!crmApi) {
      return;
    }
    setLoading(true);
    setError("");
    try {
      const [pipe, dealRows, orgRows, forecastRow, projectRows] = await Promise.all([
        crmApi.getPipeline(),
        crmApi.listDeals(),
        crmApi.listOrganizations(),
        crmApi.getDealForecast(),
        projectsApi ? projectsApi.getProjects() : Promise.resolve([]),
      ]);
      setPipeline(pipe);
      setDeals(dealRows);
      setOrgs(orgRows);
      setForecast(forecastRow);
      setProjects(projectRows);
      const queryDealId = Number(
        new URLSearchParams(window.location.search).get("deal") || 0,
      );
      if (queryDealId) {
        const fromQuery = dealRows.find((d) => d.id === queryDealId) ?? null;
        if (fromQuery) {
          setSelected(fromQuery);
        }
      } else if (selected) {
        const refreshed = dealRows.find((d) => d.id === selected.id) ?? null;
        setSelected(refreshed);
      }
    } catch (err) {
      setError(parseApiError(err, "Не удалось загрузить сделки"));
    } finally {
      setLoading(false);
    }
  }, [crmApi, projectsApi, selected?.id]);

  useEffect(() => {
    void load();
  }, [crmApi, projectsApi, workspaceEpoch]);

  useEffect(() => {
    if (!dealFromQuery || deals.length === 0) {
      return;
    }
    const match = deals.find((d) => d.id === dealFromQuery);
    if (match && selected?.id !== match.id) {
      setSelected(match);
    }
  }, [dealFromQuery, deals, selected?.id]);

  const selectDeal = (deal: CrmDeal) => {
    setSelected(deal);
    setSearchParams({ deal: String(deal.id) }, { replace: true });
  };

  const loadTasks = useCallback(async () => {
    if (!crmApi || !selected) {
      setTasks([]);
      return;
    }
    try {
      setTasks(await crmApi.listDealTasks(selected.id));
    } catch (err) {
      setError(parseApiError(err, "Не удалось загрузить задачи сделки"));
    }
  }, [crmApi, selected]);

  useEffect(() => {
    void loadTasks();
  }, [loadTasks]);

  const dealsByStage = useMemo(() => {
    const map = new Map<number, CrmDeal[]>();
    for (const deal of deals) {
      const list = map.get(deal.stage) ?? [];
      list.push(deal);
      map.set(deal.stage, list);
    }
    for (const [stageId, list] of map) {
      map.set(
        stageId,
        [...list].sort((a, b) => a.position - b.position || a.id - b.id),
      );
    }
    return map;
  }, [deals]);

  const createDeal = async (event: FormEvent) => {
    event.preventDefault();
    if (!crmApi || !form.title.trim()) {
      return;
    }
    try {
      const created = await crmApi.createDeal({
        title: form.title.trim(),
        amount: form.amount ? Number(form.amount) : 0,
        organization_id: form.organization_id || null,
        close_date: form.close_date || null,
      });
      setForm({ title: "", amount: "", organization_id: "", close_date: "" });
      setSelected(created);
      await load();
    } catch (err) {
      setError(parseApiError(err, "Не удалось создать сделку"));
    }
  };

  const moveDealToStage = async (
    deal: CrmDeal,
    stageId: number,
    position?: number,
  ) => {
    if (!crmApi) {
      return;
    }
    try {
      const updated = await crmApi.moveDeal(deal.id, {
        stage_id: stageId,
        position,
      });
      if (selected?.id === deal.id) {
        setSelected(updated);
      }
      await load();
    } catch (err) {
      setError(parseApiError(err, "Не удалось переместить сделку"));
      await load();
    }
  };

  const handleDragStart = (event: DragStartEvent) => {
    const deal = event.active.data.current?.deal as CrmDeal | undefined;
    setActiveDeal(deal ?? null);
  };

  const handleDragEnd = async (event: DragEndEvent) => {
    setActiveDeal(null);
    const { active, over } = event;
    if (!over || !pipeline) {
      return;
    }
    const deal = active.data.current?.deal as CrmDeal | undefined;
    if (!deal) {
      return;
    }

    let targetStageId: number | null = null;
    let targetIndex = 0;
    const overData = over.data.current;
    if (overData?.type === "stage") {
      targetStageId = (overData.stage as CrmPipelineStage).id;
      targetIndex = (dealsByStage.get(targetStageId) ?? []).length;
    } else if (overData?.type === "deal") {
      const overDeal = overData.deal as CrmDeal;
      targetStageId = overDeal.stage;
      const column = [...(dealsByStage.get(targetStageId) ?? [])];
      targetIndex = column.findIndex((d) => d.id === overDeal.id);
      if (targetIndex < 0) targetIndex = column.length;
    } else if (String(over.id).startsWith("stage-")) {
      targetStageId = Number(String(over.id).replace("stage-", ""));
      targetIndex = (dealsByStage.get(targetStageId) ?? []).length;
    }

    if (!targetStageId) {
      return;
    }

    // Optimistic reorder within / across columns
    const next = deals.map((d) => ({ ...d }));
    const moving = next.find((d) => d.id === deal.id);
    if (!moving) {
      return;
    }
    const fromStage = moving.stage;
    const fromList = next
      .filter((d) => d.stage === fromStage && d.id !== deal.id)
      .sort((a, b) => a.position - b.position || a.id - b.id);
    const toList = next
      .filter((d) => d.stage === targetStageId && d.id !== deal.id)
      .sort((a, b) => a.position - b.position || a.id - b.id);

    if (fromStage === targetStageId) {
      const stageList = [...(dealsByStage.get(fromStage) ?? [])];
      const oldIdx = stageList.findIndex((d) => d.id === deal.id);
      let newIdx = oldIdx;
      if (overData?.type === "deal") {
        newIdx = stageList.findIndex(
          (d) => d.id === (overData.deal as CrmDeal).id,
        );
      }
      if (oldIdx < 0 || newIdx < 0 || oldIdx === newIdx) {
        return;
      }
      const reordered = arrayMove(stageList, oldIdx, newIdx);
      const finalPosition = reordered.findIndex((d) => d.id === deal.id);
      setDeals((prev) =>
        prev.map((d) => {
          if (d.stage !== fromStage) {
            return d;
          }
          const idx = reordered.findIndex((x) => x.id === d.id);
          return idx >= 0 ? { ...d, position: idx } : d;
        }),
      );
      await moveDealToStage(deal, targetStageId, finalPosition);
      return;
    }

    moving.stage = targetStageId;
    const stage = pipeline.stages.find((s) => s.id === targetStageId);
    if (stage) {
      moving.probability = stage.default_probability;
      moving.stage_name = stage.name;
    }
    toList.splice(targetIndex, 0, moving);
    const optimistic = [
      ...next.filter((d) => d.stage !== fromStage && d.stage !== targetStageId),
      ...fromList.map((d, idx) => ({ ...d, position: idx })),
      ...toList.map((d, idx) => ({ ...d, position: idx, stage: targetStageId! })),
    ];
    setDeals(optimistic);
    await moveDealToStage(deal, targetStageId, targetIndex);
  };

  const linkProject = async (projectId: number | null) => {
    if (!crmApi || !selected) {
      return;
    }
    try {
      const updated = await crmApi.patchDeal(selected.id, {
        project_id: projectId,
      });
      setSelected(updated);
      await load();
    } catch (err) {
      setError(parseApiError(err, "Не удалось привязать проект"));
    }
  };

  const createTask = async (event: FormEvent) => {
    event.preventDefault();
    if (!crmApi || !selected || !taskTitle.trim()) {
      return;
    }
    try {
      await crmApi.createDealTask(selected.id, {
        title: taskTitle.trim(),
        due_date: taskDue || null,
      });
      setTaskTitle("");
      setTaskDue("");
      await loadTasks();
      await load();
    } catch (err) {
      setError(parseApiError(err, "Не удалось добавить задачу"));
    }
  };

  const toggleTask = async (task: CrmDealTask) => {
    if (!crmApi || !selected) {
      return;
    }
    try {
      await crmApi.patchDealTask(selected.id, task.id, {
        is_done: !task.is_done,
      });
      await loadTasks();
      await load();
    } catch (err) {
      setError(parseApiError(err, "Не удалось обновить задачу"));
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-text">Сделки</h1>
          <p className="mt-1 text-sm text-text-muted">
            Воронка с DnD · проект · прогноз
          </p>
        </div>
        {forecast && (
          <div className="rounded-xl border border-border bg-surface px-4 py-3 text-sm">
            <p className="font-semibold text-text">
              Прогноз: {money(forecast.forecast_amount)}
            </p>
            <p className="text-text-muted">
              Открыто {forecast.open_count} · {money(forecast.open_amount)} · Won{" "}
              {money(forecast.won_amount)}
            </p>
          </div>
        )}
      </div>

      {error && <ErrorMessage message={error} onDismiss={() => setError("")} />}

      <form
        onSubmit={(event) => void createDeal(event)}
        className="flex flex-wrap items-end gap-2 rounded-xl border border-border bg-surface p-4"
      >
        <div className="min-w-[12rem] flex-1">
          <label className="text-xs text-text-muted">Название</label>
          <input
            value={form.title}
            onChange={(event) =>
              setForm((prev) => ({ ...prev, title: event.target.value }))
            }
            className="mt-0.5 w-full rounded-lg border border-border bg-cream px-3 py-1.5 text-sm"
            required
          />
        </div>
        <div>
          <label className="text-xs text-text-muted">Сумма</label>
          <input
            value={form.amount}
            onChange={(event) =>
              setForm((prev) => ({ ...prev, amount: event.target.value }))
            }
            type="number"
            min="0"
            className="mt-0.5 w-28 rounded-lg border border-border bg-cream px-3 py-1.5 text-sm"
          />
        </div>
        <div>
          <label className="text-xs text-text-muted">Компания</label>
          <select
            value={form.organization_id}
            onChange={(event) =>
              setForm((prev) => ({
                ...prev,
                organization_id: event.target.value
                  ? Number(event.target.value)
                  : "",
              }))
            }
            className="mt-0.5 block rounded-lg border border-border bg-cream px-3 py-1.5 text-sm"
          >
            <option value="">—</option>
            {orgs.map((org) => (
              <option key={org.id} value={org.id}>
                {org.name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-xs text-text-muted">Close date</label>
          <input
            type="date"
            value={form.close_date}
            onChange={(event) =>
              setForm((prev) => ({ ...prev, close_date: event.target.value }))
            }
            className="mt-0.5 rounded-lg border border-border bg-cream px-3 py-1.5 text-sm"
          />
        </div>
        <button
          type="submit"
          className="rounded-lg bg-primary px-3 py-1.5 text-sm font-semibold text-white"
        >
          Создать
        </button>
      </form>

      {loading || !pipeline ? (
        <p className="text-sm text-text-muted">Загрузка воронки…</p>
      ) : (
        <DndContext
          sensors={sensors}
          collisionDetection={closestCorners}
          onDragStart={handleDragStart}
          onDragEnd={(event) => void handleDragEnd(event)}
        >
          <div className="flex gap-3 overflow-x-auto pb-2">
            {pipeline.stages.map((stage) => (
              <StageColumn
                key={stage.id}
                stage={stage}
                deals={dealsByStage.get(stage.id) ?? []}
                selectedId={selected?.id ?? null}
                onSelect={selectDeal}
              />
            ))}
          </div>
          <DragOverlay>
            {activeDeal ? (
              <div className="w-60 rounded-lg border border-primary bg-cream px-3 py-2 text-sm shadow-lg">
                <p className="font-medium text-text">{activeDeal.title}</p>
                <p className="text-xs text-text-muted">
                  {money(activeDeal.amount)} · {activeDeal.probability}%
                </p>
              </div>
            ) : null}
          </DragOverlay>
        </DndContext>
      )}

      {selected && (
        <div className="rounded-xl border border-border bg-surface p-4">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div>
              <h2 className="text-lg font-semibold text-text">{selected.title}</h2>
              <p className="text-sm text-text-muted">
                {selected.stage_name} · {money(selected.amount)} ×{" "}
                {selected.probability}% = {money(selected.weighted_amount)}
                {selected.owner_email ? ` · ${selected.owner_email}` : ""}
              </p>
            </div>
            <select
              value={selected.stage}
              onChange={(event) => {
                void moveDealToStage(selected, Number(event.target.value));
              }}
              className="rounded-lg border border-border bg-cream px-2 py-1.5 text-sm"
            >
              {pipeline?.stages.map((stage) => (
                <option key={stage.id} value={stage.id}>
                  {stage.name}
                </option>
              ))}
            </select>
          </div>

          <div className="mt-3">
            <label className="text-xs text-text-muted">Проект</label>
            <select
              value={selected.project ?? ""}
              onChange={(event) => {
                const value = event.target.value;
                void linkProject(value ? Number(value) : null);
              }}
              className="mt-0.5 block w-full max-w-md rounded-lg border border-border bg-cream px-3 py-1.5 text-sm"
            >
              <option value="">Без проекта</option>
              {projects.map((project) => (
                <option key={project.id} value={project.id}>
                  {project.name}
                </option>
              ))}
            </select>
          </div>

          <form
            onSubmit={(event) => void createTask(event)}
            className="mt-4 flex flex-wrap items-end gap-2 border-t border-border pt-3"
          >
            <div className="min-w-[12rem] flex-1">
              <label className="text-xs text-text-muted">Задача по сделке</label>
              <input
                value={taskTitle}
                onChange={(event) => setTaskTitle(event.target.value)}
                className="mt-0.5 w-full rounded-lg border border-border bg-cream px-3 py-1.5 text-sm"
                placeholder="Follow-up / КП / звонок"
                required
              />
            </div>
            <div>
              <label className="text-xs text-text-muted">Срок</label>
              <input
                type="date"
                value={taskDue}
                onChange={(event) => setTaskDue(event.target.value)}
                className="mt-0.5 rounded-lg border border-border bg-cream px-3 py-1.5 text-sm"
              />
            </div>
            <button
              type="submit"
              className="rounded-lg bg-primary px-3 py-1.5 text-sm font-semibold text-white"
            >
              Добавить
            </button>
          </form>

          <ul className="mt-3 space-y-2">
            {tasks.length === 0 ? (
              <li className="text-sm text-text-muted">Нет задач</li>
            ) : (
              tasks.map((task) => (
                <li
                  key={task.id}
                  className="flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-sm"
                >
                  <input
                    type="checkbox"
                    checked={task.is_done}
                    onChange={() => void toggleTask(task)}
                  />
                  <span
                    className={
                      task.is_done ? "text-text-muted line-through" : "text-text"
                    }
                  >
                    {task.title}
                  </span>
                  {task.due_date && (
                    <span className="ml-auto text-xs text-text-muted">
                      до {task.due_date}
                    </span>
                  )}
                </li>
              ))
            )}
          </ul>
        </div>
      )}
    </div>
  );
}
