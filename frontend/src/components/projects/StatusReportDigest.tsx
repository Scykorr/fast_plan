import type { ProjectStatusReport } from "../../api/projects";

type Props = {
  report: ProjectStatusReport;
  onExportJson?: () => void;
  onExportPdf?: () => void;
  readOnly?: boolean;
};

function formatMetric(value: number | null | undefined) {
  if (value == null) {
    return "—";
  }
  return value.toFixed(2);
}

export function StatusReportDigest({
  report,
  onExportJson,
  onExportPdf,
  readOnly = false,
}: Props) {
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-text">Статус-отчёт</h2>
          <p className="text-xs text-text-muted">
            Сформирован: {new Date(report.generated_at).toLocaleString("ru-RU")}
          </p>
        </div>
        {!readOnly && onExportJson && onExportPdf && (
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={onExportJson}
              className="rounded-lg border border-border px-4 py-2 text-sm font-medium text-text hover:bg-cream"
            >
              Экспорт JSON
            </button>
            <button
              type="button"
              onClick={onExportPdf}
              className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white hover:opacity-90"
            >
              Экспорт PDF
            </button>
          </div>
        )}
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <div className="rounded-xl border border-border bg-surface p-5">
          <p className="text-sm text-text-muted">Прогресс</p>
          <p className="mt-1 text-3xl font-bold text-secondary">
            {report.progress}%
          </p>
        </div>
        <div className="rounded-xl border border-border bg-surface p-5">
          <p className="text-sm text-text-muted">SPI / CPI</p>
          <p className="mt-1 text-2xl font-bold text-text">
            {formatMetric(report.evm.spi)} / {formatMetric(report.evm.cpi)}
          </p>
        </div>
        <div className="rounded-xl border border-border bg-surface p-5">
          <p className="text-sm text-text-muted">Сгенерировано</p>
          <p className="mt-1 text-sm font-medium text-text">
            {new Date(report.generated_at).toLocaleString("ru-RU")}
          </p>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="rounded-xl border border-border bg-surface p-5">
          <h3 className="mb-3 text-sm font-semibold text-text">Топ-риски</h3>
          {report.top_risks.length === 0 ? (
            <p className="text-sm text-text-muted">Нет рисков</p>
          ) : (
            <ul className="space-y-2 text-sm">
              {report.top_risks.slice(0, 5).map((risk) => (
                <li key={risk.id} className="flex justify-between gap-2">
                  <span className="truncate">{risk.title}</span>
                  <span className="shrink-0 font-medium text-primary">
                    {risk.score}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="rounded-xl border border-border bg-surface p-5">
          <h3 className="mb-3 text-sm font-semibold text-text">Вехи</h3>
          {report.milestones.length === 0 ? (
            <p className="text-sm text-text-muted">Нет вех</p>
          ) : (
            <ul className="space-y-2 text-sm">
              {report.milestones.slice(0, 5).map((milestone) => (
                <li key={milestone.id} className="flex justify-between gap-2">
                  <span className="truncate">
                    {milestone.code} {milestone.name}
                  </span>
                  <span className="shrink-0 text-text-muted">
                    {milestone.start_date ?? "—"}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="rounded-xl border border-border bg-surface p-5">
          <h3 className="mb-3 text-sm font-semibold text-text">Стейкхолдеры</h3>
          {report.stakeholders.length === 0 ? (
            <p className="text-sm text-text-muted">Нет стейкхолдеров</p>
          ) : (
            <ul className="space-y-2 text-sm">
              {report.stakeholders.slice(0, 5).map((person) => (
                <li key={person.id} className="flex justify-between gap-2">
                  <span className="truncate">{person.name}</span>
                  <span className="shrink-0 text-text-muted">{person.role}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
