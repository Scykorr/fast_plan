import { useCallback, useEffect, useState } from "react";

import { parseApiError } from "../api/errors";
import type { CrmAnalytics } from "../api/crm";
import { ErrorMessage } from "../components/ErrorMessage";
import { useCrmApi } from "../hooks/useCrmApi";
import { useLocale } from "../context/LocaleContext";
import { useWorkspace } from "../context/WorkspaceContext";

export function CrmAnalyticsPage() {
  const crmApi = useCrmApi();
  const { formatMoney } = useLocale();
  const { workspaceEpoch } = useWorkspace();
  const [data, setData] = useState<CrmAnalytics | null>(null);
  const [reports, setReports] = useState<
    Array<{ id: number; name: string; query: Record<string, unknown> }>
  >([]);
  const [reportName, setReportName] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!crmApi) return;
    setLoading(true);
    try {
      const [analytics, saved] = await Promise.all([
        crmApi.getAnalytics(),
        crmApi.listSavedReports(),
      ]);
      setData(analytics);
      setReports(saved);
    } catch (err) {
      setError(parseApiError(err, "Не удалось загрузить аналитику"));
    } finally {
      setLoading(false);
    }
  }, [crmApi]);

  useEffect(() => {
    void load();
  }, [load, workspaceEpoch]);

  const saveReport = async () => {
    if (!crmApi || !reportName.trim() || !data) return;
    try {
      await crmApi.createSavedReport({
        name: reportName.trim(),
        query: { metric: "dashboard_snapshot", snapshot: data },
      });
      setReportName("");
      await load();
    } catch (err) {
      setError(parseApiError(err, "Не удалось сохранить отчёт"));
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-text">CRM аналитика</h1>
        <p className="mt-1 text-sm text-text-muted">
          Конверсия, средний чек, продажи по менеджерам, источники
        </p>
      </div>
      {error && <ErrorMessage message={error} onDismiss={() => setError("")} />}
      {loading || !data ? (
        <p className="text-sm text-text-muted">Загрузка…</p>
      ) : (
        <>
          <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {[
              {
                label: "Конверсия лидов",
                value: `${data.leads.conversion_rate}%`,
                hint: `${data.leads.converted}/${data.leads.total}`,
              },
              {
                label: "Средний чек (won)",
                value: formatMoney(data.deals.avg_check),
                hint: `${data.deals.won_count} сделок`,
              },
              {
                label: "Прогноз pipeline",
                value: formatMoney(data.deals.forecast_amount),
                hint: `${data.deals.open_count} открытых`,
              },
              {
                label: "LTV / CAC lite",
                value: `${data.finance.ltv != null ? formatMoney(data.finance.ltv) : "—"} / ${
                  data.finance.cac != null ? formatMoney(data.finance.cac) : "—"
                }`,
                hint: "по won avg и expense/converted",
              },
            ].map((card) => (
              <div
                key={card.label}
                className="rounded-xl border border-border bg-surface p-4"
              >
                <p className="text-xs uppercase tracking-wide text-text-muted">
                  {card.label}
                </p>
                <p className="mt-2 text-xl font-semibold text-text">{card.value}</p>
                <p className="mt-1 text-xs text-text-muted">{card.hint}</p>
              </div>
            ))}
          </section>

          <section className="grid gap-4 lg:grid-cols-2">
            <div className="rounded-xl border border-border bg-surface p-4">
              <h2 className="text-sm font-semibold text-text">По менеджерам</h2>
              <ul className="mt-3 space-y-2 text-sm">
                {data.deals.by_owner.length === 0 ? (
                  <li className="text-text-muted">Нет данных</li>
                ) : (
                  data.deals.by_owner.map((row) => (
                    <li
                      key={String(row.owner_id)}
                      className="flex justify-between gap-2 border-b border-border/60 py-1"
                    >
                      <span>{row.owner_email || "Без owner"}</span>
                      <span className="text-text-muted">
                        won {row.won_count} · {formatMoney(row.won_amount)} · open{" "}
                        {row.open_count}
                      </span>
                    </li>
                  ))
                )}
              </ul>
            </div>
            <div className="rounded-xl border border-border bg-surface p-4">
              <h2 className="text-sm font-semibold text-text">Источники лидов</h2>
              <ul className="mt-3 space-y-2 text-sm">
                {data.leads.by_source.length === 0 ? (
                  <li className="text-text-muted">Нет данных</li>
                ) : (
                  data.leads.by_source.map((row) => (
                    <li
                      key={row.source || "—"}
                      className="flex justify-between gap-2 border-b border-border/60 py-1"
                    >
                      <span>{row.source || "—"}</span>
                      <span className="text-text-muted">
                        {row.converted}/{row.total} · {row.conversion_rate}%
                      </span>
                    </li>
                  ))
                )}
              </ul>
            </div>
          </section>

          <section className="rounded-xl border border-border bg-surface p-4 space-y-3">
            <h2 className="text-sm font-semibold text-text">Saved reports</h2>
            <div className="flex flex-wrap gap-2">
              <input
                value={reportName}
                onChange={(e) => setReportName(e.target.value)}
                placeholder="Название снимка"
                className="rounded border border-border bg-surface px-3 py-1.5 text-sm"
              />
              <button
                type="button"
                onClick={() => void saveReport()}
                className="rounded-lg bg-primary px-3 py-1.5 text-sm font-semibold text-white"
              >
                Сохранить snapshot
              </button>
            </div>
            <ul className="space-y-1 text-sm">
              {reports.map((report) => (
                <li
                  key={report.id}
                  className="flex items-center justify-between gap-2 rounded border border-border px-2 py-1"
                >
                  <span>{report.name}</span>
                  <button
                    type="button"
                    className="text-xs text-text-muted"
                    onClick={() =>
                      void crmApi
                        ?.deleteSavedReport(report.id)
                        .then(load)
                        .catch((err) =>
                          setError(parseApiError(err, "Не удалось удалить")),
                        )
                    }
                  >
                    Удалить
                  </button>
                </li>
              ))}
            </ul>
          </section>
        </>
      )}
    </div>
  );
}
