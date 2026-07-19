import type { ProjectFinance } from "../../api/finance";

type ProjectBudgetSummaryProps = {
  finance: ProjectFinance;
  title?: string;
};

function formatMoney(value: number): string {
  // toLocaleString("ru-RU") groups digits with a non-breaking or narrow
  // no-break space depending on the ICU data available; normalize to a
  // regular space for predictable rendering/testing.
  return `${value.toLocaleString("ru-RU").replace(/[\u00A0\u202F]/g, " ")} ₽`;
}

export function ProjectBudgetSummary({
  finance,
  title = "Budget vs actual",
}: ProjectBudgetSummaryProps) {
  const spentRatio =
    finance.budget > 0
      ? Math.min(100, Math.round((finance.actual_expenses / finance.budget) * 100))
      : 0;

  return (
    <div className="rounded-xl border border-border bg-surface p-5">
      <h2 className="mb-4 text-lg font-semibold text-text">{title}</h2>
      <div className="grid gap-3 sm:grid-cols-4">
        <div>
          <p className="text-xs text-text-muted">Бюджет</p>
          <p className="mt-1 text-xl font-bold text-text">{formatMoney(finance.budget)}</p>
        </div>
        <div>
          <p className="text-xs text-text-muted">Расходы</p>
          <p className="mt-1 text-xl font-bold text-primary">
            {formatMoney(finance.actual_expenses)}
          </p>
        </div>
        <div>
          <p className="text-xs text-text-muted">Доходы</p>
          <p className="mt-1 text-xl font-bold text-secondary">
            {formatMoney(finance.actual_income)}
          </p>
        </div>
        <div>
          <p className="text-xs text-text-muted">Остаток</p>
          <p
            className={[
              "mt-1 text-xl font-bold",
              finance.balance < 0 ? "text-primary" : "text-text",
            ].join(" ")}
          >
            {formatMoney(finance.balance)}
          </p>
        </div>
      </div>
      {finance.budget > 0 && (
        <div className="mt-4">
          <div className="mb-1 flex justify-between text-xs text-text-muted">
            <span>Расход бюджета</span>
            <span>{spentRatio}%</span>
          </div>
          <div className="h-2 rounded-full bg-cream">
            <div
              className="h-2 rounded-full bg-primary transition-all"
              style={{ width: `${spentRatio}%` }}
              data-testid="budget-spent-bar"
            />
          </div>
        </div>
      )}
    </div>
  );
}
