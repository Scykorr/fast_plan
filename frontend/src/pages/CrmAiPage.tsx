import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { parseApiError } from "../api/errors";
import type {
  CrmAiActivitySummary,
  CrmAiDraftEmail,
  CrmAiDraftKp,
  CrmAiInsights,
  CrmAiSuggestTasks,
  CrmDeal,
} from "../api/crm";
import { ErrorMessage } from "../components/ErrorMessage";
import { useCrmApi } from "../hooks/useCrmApi";
import { useLocale } from "../context/LocaleContext";
import { useWorkspace } from "../context/WorkspaceContext";

export function CrmAiPage() {
  const crmApi = useCrmApi();
  const { formatMoney } = useLocale();
  const { workspaceEpoch } = useWorkspace();
  const [insights, setInsights] = useState<CrmAiInsights | null>(null);
  const [deals, setDeals] = useState<CrmDeal[]>([]);
  const [dealId, setDealId] = useState<number | "">("");
  const [prompt, setPrompt] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState("");
  const [email, setEmail] = useState<CrmAiDraftEmail | null>(null);
  const [kp, setKp] = useState<CrmAiDraftKp | null>(null);
  const [summary, setSummary] = useState<CrmAiActivitySummary | null>(null);
  const [tasks, setTasks] = useState<CrmAiSuggestTasks | null>(null);

  const load = useCallback(async () => {
    if (!crmApi) {
      return;
    }
    setLoading(true);
    try {
      const [insightData, dealRows] = await Promise.all([
        crmApi.getAiInsights(14),
        crmApi.listDeals(),
      ]);
      setInsights(insightData);
      setDeals(dealRows);
      setDealId((current) => {
        if (current !== "") {
          return current;
        }
        return dealRows[0]?.id ?? "";
      });
    } catch (err) {
      setError(parseApiError(err, "Не удалось загрузить AI CRM"));
    } finally {
      setLoading(false);
    }
  }, [crmApi]);

  useEffect(() => {
    void load();
  }, [load, workspaceEpoch]);

  const targetBody = () => ({
    deal_id: dealId === "" ? undefined : dealId,
    prompt: prompt.trim() || undefined,
  });

  const runDraftEmail = async () => {
    if (!crmApi) return;
    setBusy("email");
    setError("");
    try {
      setEmail(await crmApi.draftAiEmail(targetBody()));
    } catch (err) {
      setError(parseApiError(err, "Не удалось сгенерировать письмо"));
    } finally {
      setBusy("");
    }
  };

  const runDraftKp = async () => {
    if (!crmApi) return;
    setBusy("kp");
    setError("");
    try {
      setKp(await crmApi.draftAiKp(targetBody()));
    } catch (err) {
      setError(parseApiError(err, "Не удалось сгенерировать КП"));
    } finally {
      setBusy("");
    }
  };

  const runSummary = async () => {
    if (!crmApi) return;
    setBusy("summary");
    setError("");
    try {
      setSummary(await crmApi.summarizeAiActivity(targetBody()));
    } catch (err) {
      setError(parseApiError(err, "Не удалось сделать резюме"));
    } finally {
      setBusy("");
    }
  };

  const runSuggest = async (apply: boolean) => {
    if (!crmApi || dealId === "") return;
    setBusy(apply ? "apply" : "tasks");
    setError("");
    try {
      setTasks(
        await crmApi.suggestAiTasks({
          deal_id: dealId,
          apply,
          prompt: prompt.trim() || undefined,
        }),
      );
      if (apply) {
        const refreshed = await crmApi.getAiInsights(14);
        setInsights(refreshed);
      }
    } catch (err) {
      setError(parseApiError(err, "Не удалось предложить задачи"));
    } finally {
      setBusy("");
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-text">AI CRM</h1>
        <p className="mt-1 text-sm text-text-muted">
          Insights, черновики писем/КП, резюме активности и auto-tasks
        </p>
      </div>

      {error && <ErrorMessage message={error} onDismiss={() => setError("")} />}

      <section className="rounded-xl border border-border bg-surface p-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-sm font-semibold text-text">Insights</h2>
          <button
            type="button"
            onClick={() => void load()}
            className="text-xs text-primary"
          >
            Обновить
          </button>
        </div>
        {loading || !insights ? (
          <p className="mt-2 text-sm text-text-muted">Загрузка…</p>
        ) : (
          <div className="mt-3 space-y-4">
            <p className="text-sm text-text">{insights.summary}</p>
            <p className="text-xs text-text-muted">
              source: {insights.source} · прогноз:{" "}
              {formatMoney(insights.forecast_amount)}
            </p>
            <div className="grid gap-4 lg:grid-cols-2">
              <div>
                <h3 className="text-xs font-semibold uppercase text-text-muted">
                  Клиенты без касаний ≥{insights.stale_days} дн.
                </h3>
                <ul className="mt-2 max-h-48 space-y-1 overflow-y-auto text-sm">
                  {insights.stale_people.length === 0 &&
                  insights.stale_organizations.length === 0 ? (
                    <li className="text-text-muted">Нет stale-клиентов</li>
                  ) : null}
                  {insights.stale_organizations.map((org) => (
                    <li key={`org-${org.id}`}>
                      <Link className="text-primary" to="/clients">
                        {org.name}
                      </Link>{" "}
                      <span className="text-text-muted">
                        · {org.days_since_touch ?? "∞"} дн.
                      </span>
                    </li>
                  ))}
                  {insights.stale_people.map((person) => (
                    <li key={`p-${person.id}`}>
                      {person.full_name}{" "}
                      <span className="text-text-muted">
                        · {person.days_since_touch ?? "∞"} дн.
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <h3 className="text-xs font-semibold uppercase text-text-muted">
                  Сделки под риском
                </h3>
                <ul className="mt-2 max-h-48 space-y-2 overflow-y-auto text-sm">
                  {insights.at_risk_deals.length === 0 ? (
                    <li className="text-text-muted">Рисковых сделок нет</li>
                  ) : (
                    insights.at_risk_deals.map((deal) => (
                      <li key={deal.id} className="rounded border border-border px-2 py-1">
                        <button
                          type="button"
                          className="font-medium text-primary"
                          onClick={() => setDealId(deal.id)}
                        >
                          {deal.title}
                        </button>
                        <p className="text-xs text-text-muted">
                          {formatMoney(deal.amount)} · {deal.probability}% ·{" "}
                          {deal.reasons.join("; ")}
                        </p>
                      </li>
                    ))
                  )}
                </ul>
              </div>
            </div>
          </div>
        )}
      </section>

      <section className="rounded-xl border border-border bg-surface p-4 space-y-3">
        <h2 className="text-sm font-semibold text-text">Ассистент по сделке</h2>
        <div className="grid gap-3 sm:grid-cols-[1fr_2fr]">
          <select
            value={dealId === "" ? "" : String(dealId)}
            onChange={(e) =>
              setDealId(e.target.value ? Number(e.target.value) : "")
            }
            className="rounded-lg border border-border bg-surface px-3 py-2 text-sm"
          >
            <option value="">Сделка…</option>
            {deals.map((deal) => (
              <option key={deal.id} value={deal.id}>
                {deal.title}
              </option>
            ))}
          </select>
          <input
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Доп. контекст / промпт (опционально)"
            className="rounded-lg border border-border bg-surface px-3 py-2 text-sm"
          />
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            disabled={!dealId || busy === "email"}
            onClick={() => void runDraftEmail()}
            className="rounded-lg bg-primary px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-50"
          >
            Draft email
          </button>
          <button
            type="button"
            disabled={!dealId || busy === "kp"}
            onClick={() => void runDraftKp()}
            className="rounded-lg border border-border px-3 py-1.5 text-sm disabled:opacity-50"
          >
            Draft КП
          </button>
          <button
            type="button"
            disabled={!dealId || busy === "summary"}
            onClick={() => void runSummary()}
            className="rounded-lg border border-border px-3 py-1.5 text-sm disabled:opacity-50"
          >
            Резюме активности
          </button>
          <button
            type="button"
            disabled={!dealId || busy === "tasks"}
            onClick={() => void runSuggest(false)}
            className="rounded-lg border border-border px-3 py-1.5 text-sm disabled:opacity-50"
          >
            Предложить задачи
          </button>
          <button
            type="button"
            disabled={!dealId || busy === "apply"}
            onClick={() => void runSuggest(true)}
            className="rounded-lg border border-border px-3 py-1.5 text-sm disabled:opacity-50"
          >
            Создать задачи
          </button>
        </div>

        {email && (
          <div className="rounded-lg border border-border p-3 text-sm">
            <p className="text-xs text-text-muted">Email · {email.source}</p>
            <p className="mt-1 font-medium">{email.subject}</p>
            <pre className="mt-2 whitespace-pre-wrap font-sans text-text-muted">
              {email.body}
            </pre>
          </div>
        )}
        {kp && (
          <div className="rounded-lg border border-border p-3 text-sm">
            <p className="text-xs text-text-muted">КП · {kp.source}</p>
            <p className="mt-1 font-medium">{kp.title}</p>
            <pre className="mt-2 whitespace-pre-wrap font-sans text-text-muted">
              {kp.markdown}
            </pre>
          </div>
        )}
        {summary && (
          <div className="rounded-lg border border-border p-3 text-sm">
            <p className="text-xs text-text-muted">
              Резюме · {summary.source} · {summary.count} активностей
            </p>
            <p className="mt-1">{summary.summary}</p>
            {summary.highlights.length > 0 && (
              <ul className="mt-2 list-disc pl-5 text-text-muted">
                {summary.highlights.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            )}
          </div>
        )}
        {tasks && (
          <div className="rounded-lg border border-border p-3 text-sm">
            <p className="text-xs text-text-muted">Задачи · {tasks.source}</p>
            <ul className="mt-2 space-y-1">
              {tasks.tasks.map((task) => (
                <li key={task.title}>
                  {task.title}{" "}
                  <span className="text-text-muted">
                    · +{task.due_in_days}д {task.notes ? `· ${task.notes}` : ""}
                  </span>
                </li>
              ))}
            </ul>
            {tasks.created.length > 0 && (
              <p className="mt-2 text-secondary">
                Создано: {tasks.created.map((t) => t.title).join(", ")}
              </p>
            )}
          </div>
        )}
      </section>
    </div>
  );
}
