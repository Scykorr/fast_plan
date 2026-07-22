import { useCallback, useEffect, useState, type FormEvent } from "react";

import { parseApiError } from "../api/errors";
import type {
  CrmAutomationAction,
  CrmAutomationCondition,
  CrmAutomationRule,
  CrmAutomationRun,
  CrmAutomationTemplate,
  CrmAutomationTrigger,
} from "../api/crm";
import { ErrorMessage } from "../components/ErrorMessage";
import { useCrmApi } from "../hooks/useCrmApi";
import { useWorkspace } from "../context/WorkspaceContext";

const TRIGGERS: { value: CrmAutomationTrigger; label: string }[] = [
  { value: "lead.created", label: "Лид создан" },
  { value: "lead.converted", label: "Лид конвертирован" },
  { value: "deal.created", label: "Сделка создана" },
  { value: "deal.stage_changed", label: "Смена стадии сделки" },
  { value: "schedule.daily", label: "Ежедневно (schedule.daily)" },
];

const CONDITION_FIELDS = [
  { value: "source", label: "source (лид)" },
  { value: "status", label: "status (лид)" },
  { value: "score", label: "score" },
  { value: "stage_id", label: "stage_id" },
  { value: "from_stage_id", label: "from_stage_id" },
  { value: "amount", label: "amount" },
  { value: "probability", label: "probability" },
  { value: "days_since_touch", label: "days_since_touch" },
];

const CONDITION_OPS = [
  { value: "eq", label: "=" },
  { value: "neq", label: "≠" },
  { value: "contains", label: "contains" },
  { value: "in", label: "in" },
  { value: "gte", label: "≥" },
  { value: "lte", label: "≤" },
];

const ACTION_TYPES = [
  { value: "assign_round_robin", label: "Assign round-robin" },
  { value: "assign", label: "Assign user" },
  { value: "create_deal_task", label: "Создать задачу сделки" },
  { value: "create_activity", label: "Создать активность" },
  { value: "create_deal", label: "Создать сделку (из лида)" },
  { value: "create_lead", label: "Создать лид" },
  { value: "set_status", label: "Статус лида" },
  { value: "webhook", label: "Webhook" },
  { value: "delay", label: "Delay" },
];

function emptyCondition(): CrmAutomationCondition {
  return { field: "source", op: "eq", value: "" };
}

function emptyAction(): CrmAutomationAction {
  return { type: "create_deal_task", title: "", due_in_days: 2 };
}

function parseConditionValue(raw: string, op: string): unknown {
  if (op === "in") {
    return raw
      .split(",")
      .map((part) => part.trim())
      .filter(Boolean);
  }
  if (op === "gte" || op === "lte") {
    const num = Number(raw);
    return Number.isFinite(num) ? num : raw;
  }
  return raw;
}

function conditionValueToString(value: unknown): string {
  if (Array.isArray(value)) {
    return value.map(String).join(", ");
  }
  if (value == null) {
    return "";
  }
  return String(value);
}

type EditorState = {
  id?: number;
  name: string;
  trigger: CrmAutomationTrigger;
  is_active: boolean;
  conditions: CrmAutomationCondition[];
  actions: CrmAutomationAction[];
};

function ruleToEditor(rule?: CrmAutomationRule | null): EditorState {
  if (!rule) {
    return {
      name: "",
      trigger: "lead.created",
      is_active: true,
      conditions: [],
      actions: [emptyAction()],
    };
  }
  return {
    id: rule.id,
    name: rule.name,
    trigger: (rule.trigger as CrmAutomationTrigger) || "lead.created",
    is_active: rule.is_active,
    conditions: (rule.conditions || []).map((c) => ({
      field: String(c.field || "source"),
      op: String(c.op || "eq"),
      value: c.value,
    })),
    actions: (rule.actions || []).map((a) => ({ ...a, type: String(a.type || "") })),
  };
}

function ConditionsEditor({
  conditions,
  onChange,
}: {
  conditions: CrmAutomationCondition[];
  onChange: (next: CrmAutomationCondition[]) => void;
}) {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold uppercase tracking-wide text-text-muted">
          Условия
        </p>
        <button
          type="button"
          onClick={() => onChange([...conditions, emptyCondition()])}
          className="text-xs text-primary"
        >
          + условие
        </button>
      </div>
      {conditions.length === 0 ? (
        <p className="text-xs text-text-muted">Без условий — правило срабатывает всегда</p>
      ) : (
        conditions.map((cond, index) => (
          <div
            key={index}
            className="grid gap-2 rounded-lg border border-border p-2 sm:grid-cols-[1fr_auto_1fr_auto]"
          >
            <select
              value={cond.field}
              onChange={(e) => {
                const next = [...conditions];
                next[index] = { ...cond, field: e.target.value };
                onChange(next);
              }}
              className="rounded border border-border bg-surface px-2 py-1 text-sm"
            >
              {CONDITION_FIELDS.map((f) => (
                <option key={f.value} value={f.value}>
                  {f.label}
                </option>
              ))}
            </select>
            <select
              value={cond.op}
              onChange={(e) => {
                const next = [...conditions];
                next[index] = { ...cond, op: e.target.value };
                onChange(next);
              }}
              className="rounded border border-border bg-surface px-2 py-1 text-sm"
            >
              {CONDITION_OPS.map((op) => (
                <option key={op.value} value={op.value}>
                  {op.label}
                </option>
              ))}
            </select>
            <input
              value={conditionValueToString(cond.value)}
              onChange={(e) => {
                const next = [...conditions];
                next[index] = {
                  ...cond,
                  value: parseConditionValue(e.target.value, cond.op),
                };
                onChange(next);
              }}
              placeholder={cond.op === "in" ? "a, b, c" : "значение"}
              className="rounded border border-border bg-surface px-2 py-1 text-sm"
            />
            <button
              type="button"
              onClick={() => onChange(conditions.filter((_, i) => i !== index))}
              className="text-xs text-text-muted"
            >
              ✕
            </button>
          </div>
        ))
      )}
    </div>
  );
}

function ActionsEditor({
  actions,
  onChange,
}: {
  actions: CrmAutomationAction[];
  onChange: (next: CrmAutomationAction[]) => void;
}) {
  const update = (index: number, patch: Partial<CrmAutomationAction>) => {
    const next = [...actions];
    next[index] = { ...next[index], ...patch };
    onChange(next);
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold uppercase tracking-wide text-text-muted">
          Actions
        </p>
        <button
          type="button"
          onClick={() => onChange([...actions, emptyAction()])}
          className="text-xs text-primary"
        >
          + action
        </button>
      </div>
      {actions.map((action, index) => (
        <div key={index} className="space-y-2 rounded-lg border border-border p-2">
          <div className="flex flex-wrap items-center gap-2">
            <select
              value={String(action.type || "")}
              onChange={(e) => {
                const type = e.target.value;
                const base: CrmAutomationAction = { type };
                if (type === "create_deal_task") {
                  base.title = "Follow-up";
                  base.due_in_days = 2;
                  base.skip_if_open = false;
                } else if (type === "create_activity") {
                  base.kind = "note";
                  base.subject = "";
                  base.body = "";
                } else if (type === "delay") {
                  base.minutes = 60;
                } else if (type === "assign") {
                  base.user_id = "";
                } else if (type === "set_status") {
                  base.status = "contacted";
                } else if (type === "webhook") {
                  base.event = "crm.automation";
                } else if (type === "create_lead") {
                  base.full_name = "";
                  base.source = "automation";
                }
                const next = [...actions];
                next[index] = base;
                onChange(next);
              }}
              className="rounded border border-border bg-surface px-2 py-1 text-sm"
            >
              {ACTION_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
            <button
              type="button"
              onClick={() => onChange(actions.filter((_, i) => i !== index))}
              className="ml-auto text-xs text-text-muted"
            >
              Удалить
            </button>
          </div>

          {action.type === "create_deal_task" && (
            <div className="grid gap-2 sm:grid-cols-3">
              <input
                value={String(action.title || "")}
                onChange={(e) => update(index, { title: e.target.value })}
                placeholder="Заголовок задачи"
                className="rounded border border-border bg-surface px-2 py-1 text-sm sm:col-span-2"
              />
              <input
                type="number"
                value={Number(action.due_in_days ?? 0)}
                onChange={(e) => update(index, { due_in_days: Number(e.target.value) })}
                placeholder="due_in_days"
                className="rounded border border-border bg-surface px-2 py-1 text-sm"
              />
              <label className="flex items-center gap-2 text-xs text-text-muted sm:col-span-3">
                <input
                  type="checkbox"
                  checked={Boolean(action.skip_if_open)}
                  onChange={(e) => update(index, { skip_if_open: e.target.checked })}
                />
                Не создавать, если открытая задача с тем же названием уже есть
              </label>
            </div>
          )}

          {action.type === "create_activity" && (
            <div className="grid gap-2 sm:grid-cols-2">
              <select
                value={String(action.kind || "note")}
                onChange={(e) => update(index, { kind: e.target.value })}
                className="rounded border border-border bg-surface px-2 py-1 text-sm"
              >
                {["note", "call", "email", "meeting", "invoice", "order"].map((k) => (
                  <option key={k} value={k}>
                    {k}
                  </option>
                ))}
              </select>
              <input
                value={String(action.subject || "")}
                onChange={(e) => update(index, { subject: e.target.value })}
                placeholder="Тема"
                className="rounded border border-border bg-surface px-2 py-1 text-sm"
              />
              <textarea
                value={String(action.body || "")}
                onChange={(e) => update(index, { body: e.target.value })}
                placeholder="Текст"
                rows={2}
                className="rounded border border-border bg-surface px-2 py-1 text-sm sm:col-span-2"
              />
            </div>
          )}

          {action.type === "delay" && (
            <div className="grid gap-2 sm:grid-cols-2">
              <input
                type="number"
                value={Number(action.minutes ?? 0)}
                onChange={(e) => update(index, { minutes: Number(e.target.value) })}
                placeholder="минуты"
                className="rounded border border-border bg-surface px-2 py-1 text-sm"
              />
              <input
                type="number"
                value={Number(action.days ?? 0)}
                onChange={(e) => update(index, { days: Number(e.target.value) })}
                placeholder="дни"
                className="rounded border border-border bg-surface px-2 py-1 text-sm"
              />
            </div>
          )}

          {action.type === "assign" && (
            <input
              value={String(action.user_id ?? "")}
              onChange={(e) => update(index, { user_id: e.target.value })}
              placeholder="user_id"
              className="w-full rounded border border-border bg-surface px-2 py-1 text-sm"
            />
          )}

          {action.type === "set_status" && (
            <select
              value={String(action.status || "contacted")}
              onChange={(e) => update(index, { status: e.target.value })}
              className="rounded border border-border bg-surface px-2 py-1 text-sm"
            >
              {["new", "contacted", "qualified", "disqualified", "converted"].map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          )}

          {action.type === "webhook" && (
            <input
              value={String(action.event || "")}
              onChange={(e) => update(index, { event: e.target.value })}
              placeholder="event name"
              className="w-full rounded border border-border bg-surface px-2 py-1 text-sm"
            />
          )}

          {action.type === "create_lead" && (
            <div className="grid gap-2 sm:grid-cols-2">
              <input
                value={String(action.full_name || "")}
                onChange={(e) => update(index, { full_name: e.target.value })}
                placeholder="ФИО"
                className="rounded border border-border bg-surface px-2 py-1 text-sm"
              />
              <input
                value={String(action.source || "")}
                onChange={(e) => update(index, { source: e.target.value })}
                placeholder="source"
                className="rounded border border-border bg-surface px-2 py-1 text-sm"
              />
            </div>
          )}

          {action.type === "create_deal" && (
            <div className="grid gap-2 sm:grid-cols-2">
              <input
                value={String(action.title || "")}
                onChange={(e) => update(index, { title: e.target.value })}
                placeholder="Название сделки"
                className="rounded border border-border bg-surface px-2 py-1 text-sm"
              />
              <input
                value={String(action.amount ?? "")}
                onChange={(e) => update(index, { amount: e.target.value })}
                placeholder="amount"
                className="rounded border border-border bg-surface px-2 py-1 text-sm"
              />
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

export function AutomationsPage() {
  const crmApi = useCrmApi();
  const { workspaceEpoch } = useWorkspace();
  const [rules, setRules] = useState<CrmAutomationRule[]>([]);
  const [templates, setTemplates] = useState<CrmAutomationTemplate[]>([]);
  const [runs, setRuns] = useState<CrmAutomationRun[]>([]);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const [editor, setEditor] = useState<EditorState>(() => ruleToEditor(null));
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    if (!crmApi) {
      return;
    }
    setLoading(true);
    try {
      const [ruleRows, templateRows, runRows] = await Promise.all([
        crmApi.listAutomations(),
        crmApi.listAutomationTemplates(),
        crmApi.listAutomationRuns(),
      ]);
      setRules(ruleRows);
      setTemplates(templateRows);
      setRuns(runRows);
    } catch (err) {
      setError(parseApiError(err, "Не удалось загрузить автоматизации"));
    } finally {
      setLoading(false);
    }
  }, [crmApi]);

  useEffect(() => {
    void load();
  }, [load, workspaceEpoch]);

  const applyTemplate = async (key: string) => {
    if (!crmApi) {
      return;
    }
    try {
      const rule = await crmApi.applyAutomationTemplate(key);
      setMessage(`Шаблон применён: ${rule.name}`);
      setEditor(ruleToEditor(rule));
      await load();
    } catch (err) {
      setError(parseApiError(err, "Не удалось применить шаблон"));
    }
  };

  const toggleActive = async (rule: CrmAutomationRule) => {
    if (!crmApi) {
      return;
    }
    try {
      await crmApi.patchAutomation(rule.id, { is_active: !rule.is_active });
      await load();
    } catch (err) {
      setError(parseApiError(err, "Не удалось обновить правило"));
    }
  };

  const removeRule = async (rule: CrmAutomationRule) => {
    if (!crmApi) {
      return;
    }
    try {
      await crmApi.deleteAutomation(rule.id);
      if (editor.id === rule.id) {
        setEditor(ruleToEditor(null));
      }
      await load();
    } catch (err) {
      setError(parseApiError(err, "Не удалось удалить"));
    }
  };

  const saveRule = async (event: FormEvent) => {
    event.preventDefault();
    if (!crmApi || !editor.name.trim()) {
      return;
    }
    setSaving(true);
    setError("");
    try {
      const body = {
        name: editor.name.trim(),
        trigger: editor.trigger,
        is_active: editor.is_active,
        conditions: editor.conditions,
        actions: editor.actions,
      };
      const saved = editor.id
        ? await crmApi.patchAutomation(editor.id, body)
        : await crmApi.createAutomation(body);
      setMessage(editor.id ? "Правило обновлено" : "Правило создано");
      setEditor(ruleToEditor(saved));
      await load();
    } catch (err) {
      setError(parseApiError(err, "Не удалось сохранить правило"));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-text">Автоматизации</h1>
        <p className="mt-1 text-sm text-text-muted">
          BPM-lite: визуальный редактор trigger → conditions → actions
        </p>
      </div>

      {error && <ErrorMessage message={error} onDismiss={() => setError("")} />}
      {message && <p className="text-sm text-secondary">{message}</p>}

      <section className="rounded-xl border border-border bg-surface p-4">
        <h2 className="text-sm font-semibold text-text">Шаблоны</h2>
        <ul className="mt-3 space-y-2">
          {templates.map((template) => (
            <li
              key={template.key}
              className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-border px-3 py-2 text-sm"
            >
              <div>
                <p className="font-medium text-text">{template.name}</p>
                <p className="text-xs text-text-muted">
                  {template.trigger} · {template.conditions.length} cond ·{" "}
                  {template.actions.length} act
                </p>
              </div>
              <button
                type="button"
                onClick={() => void applyTemplate(template.key)}
                className="rounded-lg bg-primary px-3 py-1.5 text-sm font-semibold text-white"
              >
                Применить
              </button>
            </li>
          ))}
        </ul>
      </section>

      <section className="rounded-xl border border-border bg-surface p-4">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-sm font-semibold text-text">
            {editor.id ? `Редактирование #${editor.id}` : "Новое правило"}
          </h2>
          {editor.id ? (
            <button
              type="button"
              onClick={() => setEditor(ruleToEditor(null))}
              className="text-xs text-primary"
            >
              Создать новое
            </button>
          ) : null}
        </div>
        <form onSubmit={(e) => void saveRule(e)} className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2">
            <input
              value={editor.name}
              onChange={(e) => setEditor({ ...editor, name: e.target.value })}
              placeholder="Название правила"
              required
              className="rounded-lg border border-border bg-surface px-3 py-2 text-sm"
            />
            <select
              value={editor.trigger}
              onChange={(e) =>
                setEditor({
                  ...editor,
                  trigger: e.target.value as CrmAutomationTrigger,
                })
              }
              className="rounded-lg border border-border bg-surface px-3 py-2 text-sm"
            >
              {TRIGGERS.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
          </div>
          <label className="flex items-center gap-2 text-sm text-text">
            <input
              type="checkbox"
              checked={editor.is_active}
              onChange={(e) => setEditor({ ...editor, is_active: e.target.checked })}
            />
            Активно
          </label>
          <ConditionsEditor
            conditions={editor.conditions}
            onChange={(conditions) => setEditor({ ...editor, conditions })}
          />
          <ActionsEditor
            actions={editor.actions}
            onChange={(actions) => setEditor({ ...editor, actions })}
          />
          <button
            type="submit"
            disabled={saving}
            className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
          >
            {saving ? "Сохранение…" : editor.id ? "Сохранить" : "Создать"}
          </button>
        </form>
      </section>

      <section className="rounded-xl border border-border bg-surface p-4">
        <h2 className="text-sm font-semibold text-text">Правила</h2>
        {loading ? (
          <p className="mt-2 text-sm text-text-muted">Загрузка…</p>
        ) : rules.length === 0 ? (
          <p className="mt-2 text-sm text-text-muted">
            Пока нет правил — примените шаблон или создайте выше.
          </p>
        ) : (
          <ul className="mt-3 space-y-2">
            {rules.map((rule) => (
              <li
                key={rule.id}
                className={`rounded-lg border px-3 py-2 text-sm ${
                  editor.id === rule.id ? "border-primary" : "border-border"
                }`}
              >
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <button
                    type="button"
                    onClick={() => setEditor(ruleToEditor(rule))}
                    className="text-left"
                  >
                    <p className="font-medium text-text">{rule.name}</p>
                    <p className="text-xs text-text-muted">
                      {rule.trigger}
                      {rule.template_key ? ` · ${rule.template_key}` : ""} ·{" "}
                      {rule.conditions.length} cond · {rule.actions.length} act
                    </p>
                    <p className="mt-1 text-xs text-text-muted">
                      {(rule.conditions || [])
                        .map(
                          (c) =>
                            `${c.field} ${c.op} ${conditionValueToString(c.value)}`,
                        )
                        .join("; ") || "без условий"}
                      {" → "}
                      {(rule.actions || []).map((a) => a.type).join(", ") || "—"}
                    </p>
                  </button>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => setEditor(ruleToEditor(rule))}
                      className="rounded border border-border px-2 py-1 text-xs"
                    >
                      Править
                    </button>
                    <button
                      type="button"
                      onClick={() => void toggleActive(rule)}
                      className="rounded border border-border px-2 py-1 text-xs"
                    >
                      {rule.is_active ? "Выкл" : "Вкл"}
                    </button>
                    <button
                      type="button"
                      onClick={() => void removeRule(rule)}
                      className="rounded border border-border px-2 py-1 text-xs text-text-muted"
                    >
                      Удалить
                    </button>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="rounded-xl border border-border bg-surface p-4">
        <h2 className="text-sm font-semibold text-text">Последние запуски</h2>
        {runs.length === 0 ? (
          <p className="mt-2 text-sm text-text-muted">Пока нет запусков</p>
        ) : (
          <ul className="mt-3 max-h-64 space-y-2 overflow-y-auto">
            {runs.map((run) => (
              <li
                key={run.id}
                className="rounded-lg border border-border px-3 py-2 text-xs"
              >
                <span className={run.success ? "text-secondary" : "text-amber-700"}>
                  {run.success ? "OK" : "ERR"}
                </span>{" "}
                {run.rule_name} · {run.trigger} ·{" "}
                {new Date(run.created_at).toLocaleString("ru-RU")}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
