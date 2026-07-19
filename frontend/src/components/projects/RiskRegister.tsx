import type { Risk } from "../../api/projects";

type RiskHeatMapProps = {
  risks: Risk[];
};

export function RiskHeatMap({ risks }: RiskHeatMapProps) {
  const levels = [1, 2, 3, 4, 5];

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[280px] border-collapse text-center text-xs">
        <thead>
          <tr>
            <th className="p-2 text-left text-text-muted">Влияние →</th>
            {levels.map((level) => (
              <th key={level} className="p-2 text-text-muted">
                {level}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {levels.map((impact) => (
            <tr key={impact}>
              <td className="p-2 text-left font-medium text-text">{impact}</td>
              {levels.map((probability) => {
                const count = risks.filter(
                  (risk) => risk.probability === probability && risk.impact === impact,
                ).length;
                const score = probability * impact;
                const tone =
                  score >= 15
                    ? "bg-primary/20 text-primary"
                    : score >= 9
                      ? "bg-accent/30 text-text"
                      : "bg-cream text-text-muted";
                return (
                  <td key={probability} className="p-1">
                    <div
                      className={`rounded-md py-3 font-semibold ${tone}`}
                      title={`P${probability} × I${impact}`}
                    >
                      {count || "·"}
                    </div>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-2 text-xs text-text-muted">Вероятность ↓ по строкам</p>
    </div>
  );
}

type RiskRegisterProps = {
  risks: Risk[];
  highlightedRiskId?: number | null;
  onAdd: () => void;
  onDelete: (id: number) => void;
};

export function RiskRegister({
  risks,
  highlightedRiskId = null,
  onAdd,
  onDelete,
}: RiskRegisterProps) {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-text">Реестр рисков</h2>
        <button
          type="button"
          onClick={onAdd}
          className="rounded-lg bg-primary px-3 py-1.5 text-sm font-semibold text-white hover:bg-primary-hover"
        >
          + Риск
        </button>
      </div>
      <RiskHeatMap risks={risks} />
      {risks.length === 0 ? (
        <p className="text-sm text-text-muted">Риски не зарегистрированы</p>
      ) : (
        <ul className="space-y-2">
          {risks.map((risk) => (
            <li
              key={risk.id}
              id={`risk-${risk.id}`}
              data-highlighted={
                highlightedRiskId === risk.id ? "true" : undefined
              }
              className={[
                "flex items-start justify-between gap-4 rounded-lg border bg-surface px-4 py-3",
                highlightedRiskId === risk.id
                  ? "border-primary ring-2 ring-primary/40"
                  : "border-border",
              ].join(" ")}
            >
              <div>
                <p className="font-medium text-text">{risk.title}</p>
                <p className="mt-1 text-xs text-text-muted">
                  P{risk.probability} × I{risk.impact} = {risk.score} · {risk.status}
                </p>
              </div>
              <button
                type="button"
                onClick={() => onDelete(risk.id)}
                className="text-sm text-text-muted hover:text-primary"
              >
                Удалить
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
