import { useCallback, useEffect, useState } from "react";

import { parseApiError } from "../api/errors";
import type {
  CrmAutomationRule,
  CrmAutomationRun,
  CrmAutomationTemplate,
} from "../api/crm";
import { ErrorMessage } from "../components/ErrorMessage";
import { useCrmApi } from "../hooks/useCrmApi";
import { useWorkspace } from "../context/WorkspaceContext";

export function AutomationsPage() {
  const crmApi = useCrmApi();
  const { workspaceEpoch } = useWorkspace();
  const [rules, setRules] = useState<CrmAutomationRule[]>([]);
  const [templates, setTemplates] = useState<CrmAutomationTemplate[]>([]);
  const [runs, setRuns] = useState<CrmAutomationRun[]>([]);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);

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
      await load();
    } catch (err) {
      setError(parseApiError(err, "Не удалось удалить"));
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-text">Автоматизации</h1>
        <p className="mt-1 text-sm text-text-muted">
          BPM-lite: trigger → conditions → actions (P6e)
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
                  {template.trigger} · {template.actions.length} actions
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
        <h2 className="text-sm font-semibold text-text">Правила</h2>
        {loading ? (
          <p className="mt-2 text-sm text-text-muted">Загрузка…</p>
        ) : rules.length === 0 ? (
          <p className="mt-2 text-sm text-text-muted">
            Пока нет правил — примените шаблон выше.
          </p>
        ) : (
          <ul className="mt-3 space-y-2">
            {rules.map((rule) => (
              <li
                key={rule.id}
                className="rounded-lg border border-border px-3 py-2 text-sm"
              >
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <p className="font-medium text-text">{rule.name}</p>
                    <p className="text-xs text-text-muted">
                      {rule.trigger}
                      {rule.template_key ? ` · ${rule.template_key}` : ""} ·{" "}
                      {rule.conditions.length} cond · {rule.actions.length} act
                    </p>
                  </div>
                  <div className="flex gap-2">
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
                <pre className="mt-2 overflow-x-auto rounded bg-cream/60 p-2 text-[11px] text-text-muted">
                  {JSON.stringify(
                    { conditions: rule.conditions, actions: rule.actions },
                    null,
                    2,
                  )}
                </pre>
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
