import { useState } from "react";

import type { ProcessWorkNode } from "../../api/process";
import { GlossaryText, TermHint } from "../TermHint";

type Props = {
  tree: ProcessWorkNode[];
  onSelectBpmn?: (bpmnId: string) => void;
  onPatch?: (
    nodeId: number,
    body: Record<string, unknown>,
  ) => Promise<ProcessWorkNode[]>;
};

function flatten(nodes: ProcessWorkNode[], depth = 0): Array<ProcessWorkNode & { depth: number }> {
  const out: Array<ProcessWorkNode & { depth: number }> = [];
  for (const n of nodes) {
    out.push({ ...n, depth });
    out.push(...flatten(n.children || [], depth + 1));
  }
  return out;
}

export function ProcessWorkTree({ tree, onSelectBpmn, onPatch }: Props) {
  const rows = flatten(tree);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [raciDraft, setRaciDraft] = useState({ r: "", a: "", c: "", i: "" });
  const [datesDraft, setDatesDraft] = useState({
    start: "",
    end: "",
    duration: "1",
  });

  if (rows.length === 0) {
    return (
      <p className="text-sm text-text-muted">
        Дерево ещё не материализовано. Нажмите «Materialize WBS».
      </p>
    );
  }

  return (
    <div className="space-y-3">
      <div className="overflow-x-auto rounded-lg border border-border">
        <table className="min-w-full text-left text-xs">
          <thead className="bg-cream text-text-muted">
            <tr>
              <th className="px-2 py-1.5">Код / узел</th>
              <th className="px-2 py-1.5">Тип</th>
              <th className="px-2 py-1.5">Статус</th>
              <th className="px-2 py-1.5">%</th>
              <th className="px-2 py-1.5">Даты</th>
              <th className="px-2 py-1.5">
                <TermHint term="raci">RACI</TermHint>
              </th>
              <th className="px-2 py-1.5" />
            </tr>
          </thead>
          <tbody>
            {rows.map((node) => (
              <tr key={node.id} className="border-t border-border align-top">
                <td className="px-2 py-1.5">
                  <button
                    type="button"
                    className="text-left hover:text-primary"
                    style={{ paddingLeft: node.depth * 12 }}
                    onClick={() =>
                      node.bpmn_id && !node.bpmn_id.startsWith("__root__")
                        ? onSelectBpmn?.(node.bpmn_id)
                        : undefined
                    }
                  >
                    <span className="font-medium text-text">
                      {node.code} {node.title}
                    </span>
                    {node.assignee_name && (
                      <span className="ml-1 text-text-muted">
                        · {node.assignee_name}
                      </span>
                    )}
                  </button>
                </td>
                <td className="px-2 py-1.5 text-text-muted">{node.node_type}</td>
                <td className="px-2 py-1.5">{node.status}</td>
                <td className="px-2 py-1.5">{node.progress}</td>
                <td className="px-2 py-1.5 text-text-muted">
                  {node.start_date || "—"} → {node.end_date || "—"} (
                  {node.duration_days}д)
                  {node.predecessor_bpmn_id ? (
                    <div className="text-[10px]">
                      FS ← {node.predecessor_bpmn_id}
                    </div>
                  ) : null}
                </td>
                <td className="px-2 py-1.5 text-text-muted">
                  R:{node.raci_r || "—"} A:{node.raci_a || "—"} C:
                  {node.raci_c || "—"} I:{node.raci_i || "—"}
                </td>
                <td className="px-2 py-1.5">
                  {onPatch && (
                    <button
                      type="button"
                      className="text-primary hover:underline"
                      onClick={() => {
                        setEditingId(node.id);
                        setRaciDraft({
                          r: node.raci_r,
                          a: node.raci_a,
                          c: node.raci_c,
                          i: node.raci_i,
                        });
                        setDatesDraft({
                          start: node.start_date || "",
                          end: node.end_date || "",
                          duration: String(node.duration_days || 1),
                        });
                      }}
                    >
                      Edit
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {editingId != null && onPatch && (
        <div className="rounded-lg border border-border bg-cream p-3 text-xs space-y-2">
          <p className="font-medium text-text">
            Узел #{editingId} · даты / <GlossaryText text="RACI" />
          </p>
          <div className="flex flex-wrap gap-2">
            <input
              type="date"
              value={datesDraft.start}
              onChange={(e) =>
                setDatesDraft((d) => ({ ...d, start: e.target.value }))
              }
              className="rounded border border-border bg-surface px-2 py-1"
            />
            <input
              type="date"
              value={datesDraft.end}
              onChange={(e) =>
                setDatesDraft((d) => ({ ...d, end: e.target.value }))
              }
              className="rounded border border-border bg-surface px-2 py-1"
            />
            <input
              type="number"
              min={1}
              value={datesDraft.duration}
              onChange={(e) =>
                setDatesDraft((d) => ({ ...d, duration: e.target.value }))
              }
              className="w-16 rounded border border-border bg-surface px-2 py-1"
              aria-label="duration"
            />
            {(["r", "a", "c", "i"] as const).map((k) => (
              <input
                key={k}
                placeholder={k.toUpperCase()}
                value={raciDraft[k]}
                onChange={(e) =>
                  setRaciDraft((d) => ({ ...d, [k]: e.target.value }))
                }
                className="w-20 rounded border border-border bg-surface px-2 py-1"
              />
            ))}
          </div>
          <div className="flex gap-2">
            <button
              type="button"
              className="rounded bg-primary px-3 py-1 text-white"
              onClick={() =>
                void (async () => {
                  await onPatch(editingId, {
                    start_date: datesDraft.start || null,
                    end_date: datesDraft.end || null,
                    duration_days: Number(datesDraft.duration) || 1,
                    raci_r: raciDraft.r,
                    raci_a: raciDraft.a,
                    raci_c: raciDraft.c,
                    raci_i: raciDraft.i,
                  });
                  setEditingId(null);
                })()
              }
            >
              Сохранить
            </button>
            <button
              type="button"
              className="rounded border border-border px-3 py-1"
              onClick={() => setEditingId(null)}
            >
              Отмена
            </button>
          </div>
        </div>
      )}

      <div className="space-y-1">
        <p className="text-xs font-medium text-text">
          <GlossaryText text="Gantt" />-lite
        </p>
        <div className="space-y-1">
          {rows
            .filter((n) => n.node_type !== "root")
            .map((n) => (
              <div key={`g-${n.id}`} className="flex items-center gap-2 text-[11px]">
                <span className="w-40 truncate text-text-muted">
                  {n.code} {n.title}
                </span>
                <div className="h-2 flex-1 rounded bg-border/40">
                  <div
                    className="h-2 rounded bg-secondary"
                    style={{ width: `${Math.min(100, n.progress || 5)}%` }}
                  />
                </div>
              </div>
            ))}
        </div>
      </div>
    </div>
  );
}
