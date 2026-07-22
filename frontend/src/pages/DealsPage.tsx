import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";

import { parseApiError } from "../api/errors";
import type {
  CrmDeal,
  CrmDealForecast,
  CrmDealTask,
  CrmOrganization,
  CrmPipeline,
  CrmPipelineStage,
} from "../api/crm";
import { ErrorMessage } from "../components/ErrorMessage";
import { useCrmApi } from "../hooks/useCrmApi";
import { useWorkspace } from "../context/WorkspaceContext";

function money(value: string | number | undefined) {
  const n = typeof value === "string" ? Number(value) : value ?? 0;
  return n.toLocaleString("ru-RU", { maximumFractionDigits: 0 });
}

export function DealsPage() {
  const crmApi = useCrmApi();
  const { workspaceEpoch } = useWorkspace();
  const [pipeline, setPipeline] = useState<CrmPipeline | null>(null);
  const [deals, setDeals] = useState<CrmDeal[]>([]);
  const [orgs, setOrgs] = useState<CrmOrganization[]>([]);
  const [forecast, setForecast] = useState<CrmDealForecast | null>(null);
  const [selected, setSelected] = useState<CrmDeal | null>(null);
  const [tasks, setTasks] = useState<CrmDealTask[]>([]);
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

  const load = useCallback(async () => {
    if (!crmApi) {
      return;
    }
    setLoading(true);
    setError("");
    try {
      const [pipe, dealRows, orgRows, forecastRow] = await Promise.all([
        crmApi.getPipeline(),
        crmApi.listDeals(),
        crmApi.listOrganizations(),
        crmApi.getDealForecast(),
      ]);
      setPipeline(pipe);
      setDeals(dealRows);
      setOrgs(orgRows);
      setForecast(forecastRow);
    } catch (err) {
      setError(parseApiError(err, "Не удалось загрузить сделки"));
    } finally {
      setLoading(false);
    }
  }, [crmApi]);

  useEffect(() => {
    void load();
  }, [load, workspaceEpoch]);

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

  const moveDeal = async (deal: CrmDeal, stage: CrmPipelineStage) => {
    if (!crmApi || deal.stage === stage.id) {
      return;
    }
    try {
      const updated = await crmApi.moveDeal(deal.id, { stage_id: stage.id });
      if (selected?.id === deal.id) {
        setSelected(updated);
      }
      await load();
    } catch (err) {
      setError(parseApiError(err, "Не удалось переместить сделку"));
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
            Воронка продаж · сумма · вероятность · прогноз (P6c)
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
        <div className="flex gap-3 overflow-x-auto pb-2">
          {pipeline.stages.map((stage) => {
            const stageDeals = dealsByStage.get(stage.id) ?? [];
            return (
              <div
                key={stage.id}
                className="w-64 shrink-0 rounded-xl border border-border bg-surface"
              >
                <div className="border-b border-border px-3 py-2">
                  <p className="text-sm font-semibold text-text">{stage.name}</p>
                  <p className="text-xs text-text-muted">
                    {stage.default_probability}% · {stageDeals.length}
                  </p>
                </div>
                <ul className="max-h-[28rem] space-y-2 overflow-y-auto p-2">
                  {stageDeals.length === 0 && (
                    <li className="px-2 py-4 text-center text-xs text-text-muted">
                      Пусто
                    </li>
                  )}
                  {stageDeals.map((deal) => (
                    <li key={deal.id}>
                      <button
                        type="button"
                        onClick={() => setSelected(deal)}
                        className={`w-full rounded-lg border px-3 py-2 text-left text-sm ${
                          selected?.id === deal.id
                            ? "border-primary bg-cream"
                            : "border-border bg-cream/40 hover:border-primary/50"
                        }`}
                      >
                        <p className="font-medium text-text">{deal.title}</p>
                        <p className="text-xs text-text-muted">
                          {money(deal.amount)} · {deal.probability}%
                          {deal.organization_name
                            ? ` · ${deal.organization_name}`
                            : ""}
                        </p>
                        {(deal.open_tasks_count ?? 0) > 0 && (
                          <p className="mt-1 text-[10px] text-amber-700 dark:text-amber-300">
                            Задач: {deal.open_tasks_count}
                          </p>
                        )}
                      </button>
                      <div className="mt-1 flex flex-wrap gap-1 px-1">
                        {pipeline.stages
                          .filter((s) => s.id !== stage.id)
                          .slice(0, 3)
                          .map((target) => (
                            <button
                              key={target.id}
                              type="button"
                              onClick={() => void moveDeal(deal, target)}
                              className="rounded border border-border px-1.5 py-0.5 text-[10px] text-text-muted hover:border-primary"
                              title={`Переместить в ${target.name}`}
                            >
                              → {target.name}
                            </button>
                          ))}
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            );
          })}
        </div>
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
                const stage = pipeline?.stages.find(
                  (s) => s.id === Number(event.target.value),
                );
                if (stage) {
                  void moveDeal(selected, stage);
                }
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
