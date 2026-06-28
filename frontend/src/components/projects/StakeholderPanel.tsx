import type { RACIEntry, Stakeholder, WBSNode } from "../../api/projects";

type StakeholderPanelProps = {
  stakeholders: Stakeholder[];
  raci: RACIEntry[];
  wbs: WBSNode[];
  onAddStakeholder: () => void;
  onDeleteStakeholder: (id: number) => void;
  onAddRACI: () => void;
  onDeleteRACI: (id: number) => void;
};

function flattenWBS(nodes: WBSNode[]): WBSNode[] {
  return nodes.flatMap((node) => [node, ...flattenWBS(node.children)]);
}

export function StakeholderPanel({
  stakeholders,
  raci,
  wbs,
  onAddStakeholder,
  onDeleteStakeholder,
  onAddRACI,
  onDeleteRACI,
}: StakeholderPanelProps) {
  const wbsNodes = flattenWBS(wbs);

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <div className="rounded-xl border border-border bg-surface p-4">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-text">Стейкхолдеры</h2>
          <button
            type="button"
            onClick={onAddStakeholder}
            className="text-sm font-medium text-primary hover:underline"
          >
            + Добавить
          </button>
        </div>
        {stakeholders.length === 0 ? (
          <p className="text-sm text-text-muted">Список пуст</p>
        ) : (
          <ul className="space-y-2">
            {stakeholders.map((item) => (
              <li
                key={item.id}
                className="rounded-lg border border-border px-3 py-2 text-sm"
              >
                <div className="flex justify-between gap-2">
                  <div>
                    <p className="font-medium">{item.name}</p>
                    <p className="text-xs text-text-muted">
                      {item.role || "—"} · интерес {item.interest} · влияние{" "}
                      {item.influence}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => onDeleteStakeholder(item.id)}
                    className="text-xs text-text-muted hover:text-primary"
                  >
                    ×
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="rounded-xl border border-border bg-surface p-4">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-text">RACI-матрица</h2>
          <button
            type="button"
            onClick={onAddRACI}
            disabled={stakeholders.length === 0 || wbsNodes.length === 0}
            className="text-sm font-medium text-primary hover:underline disabled:opacity-50"
          >
            + Назначение
          </button>
        </div>
        {raci.length === 0 ? (
          <p className="text-sm text-text-muted">Назначения не созданы</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-text-muted">
                  <th className="py-2 pr-3">WBS</th>
                  <th className="py-2 pr-3">Стейкхолдер</th>
                  <th className="py-2">RACI</th>
                  <th className="py-2" />
                </tr>
              </thead>
              <tbody>
                {raci.map((entry) => (
                  <tr key={entry.id} className="border-b border-border/60">
                    <td className="py-2 pr-3 font-mono text-xs">
                      {entry.wbs_code}
                    </td>
                    <td className="py-2 pr-3">{entry.stakeholder_name}</td>
                    <td className="py-2 font-semibold text-secondary">
                      {entry.raci_type}
                    </td>
                    <td className="py-2 text-right">
                      <button
                        type="button"
                        onClick={() => onDeleteRACI(entry.id)}
                        className="text-xs text-text-muted hover:text-primary"
                      >
                        ×
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
