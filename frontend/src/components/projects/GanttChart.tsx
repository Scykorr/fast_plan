import Gantt from "frappe-gantt";
import { useEffect, useRef, useState } from "react";

import type {
  ActivityDependency,
  LevelingProposal,
  LevelingProposeResult,
  ScheduleActivity,
} from "../../api/projects";
import { parseApiError } from "../../api/errors";
import { GlossaryText, TermHint } from "../TermHint";

type UndoBatch = {
  items: Array<{
    activity_id: number;
    start_date: string | null;
    end_date: string | null;
    duration_days?: number;
  }>;
};

type GanttChartProps = {
  activities: ScheduleActivity[];
  dependencies: ActivityDependency[];
  onProposeLeveling?: () => Promise<LevelingProposeResult>;
  onApplyProposals?: (proposals: LevelingProposal[]) => Promise<UndoBatch>;
  onUndoLeveling?: (batch: UndoBatch) => Promise<void>;
  onApplyProposal?: (proposal: LevelingProposal) => Promise<void>;
};

function buildDependenciesMap(dependencies: ActivityDependency[]) {
  const map = new Map<number, string[]>();
  for (const dep of dependencies) {
    const list = map.get(dep.successor_id) ?? [];
    list.push(`${dep.predecessor_id}${dep.dependency_type}`);
    map.set(dep.successor_id, list);
  }
  return map;
}

function customClassFor(activity: ScheduleActivity): string {
  const classes: string[] = [];
  if (activity.is_milestone) classes.push("bar-milestone");
  if (activity.capacity_hint?.overloaded) classes.push("bar-overloaded");
  return classes.join(" ");
}

export function GanttChart({
  activities,
  dependencies,
  onProposeLeveling,
  onApplyProposals,
  onUndoLeveling,
  onApplyProposal,
}: GanttChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const ganttRef = useRef<Gantt | null>(null);
  const overloadedCount = activities.filter(
    (a) => a.capacity_hint?.overloaded,
  ).length;
  const [proposals, setProposals] = useState<LevelingProposeResult | null>(null);
  const [undoBatch, setUndoBatch] = useState<UndoBatch | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (!containerRef.current || activities.length === 0) {
      return;
    }

    const depMap = buildDependenciesMap(dependencies);
    const tasks = activities
      .filter((activity) => activity.start_date && activity.end_date)
      .map((activity) => {
        const assignee = activity.assignee_name
          ? ` · ${activity.assignee_name}`
          : "";
        const overload = activity.capacity_hint?.hint
          ? ` · ${activity.capacity_hint.hint}`
          : "";
        return {
          id: String(activity.id),
          name: `${activity.code} ${activity.name}${assignee}${overload}`,
          start: activity.start_date!,
          end: activity.end_date!,
          progress: activity.progress,
          dependencies: (depMap.get(activity.id) ?? []).join(","),
          custom_class: customClassFor(activity),
        };
      });

    containerRef.current.innerHTML = "";
    ganttRef.current = new Gantt(containerRef.current, tasks, {
      view_mode: "Week",
      bar_corner_radius: 4,
      bar_height: 28,
      padding: 18,
      language: "ru",
    });

    return () => {
      ganttRef.current = null;
    };
  }, [activities, dependencies]);

  if (activities.length === 0) {
    return (
      <p className="text-sm text-text-muted">
        Добавьте work packages в WBS — они появятся на диаграмме Ганта.
      </p>
    );
  }

  const propose = async () => {
    if (!onProposeLeveling) return;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const result = await onProposeLeveling();
      setProposals(result);
      setMessage(
        result.proposals.length
          ? `Предложено сдвигов: ${result.proposals.length}`
          : "Нет предложений (перегруз не снят автоматически)",
      );
    } catch (err) {
      setError(parseApiError(err, "Не удалось предложить сдвиг"));
    } finally {
      setBusy(false);
    }
  };

  const applyOne = async (proposal: LevelingProposal) => {
    if (!onApplyProposal) return;
    setBusy(true);
    setError("");
    try {
      await onApplyProposal(proposal);
      setProposals((prev) =>
        prev
          ? {
              ...prev,
              proposals: prev.proposals.filter(
                (p) => p.activity_id !== proposal.activity_id,
              ),
            }
          : prev,
      );
      setMessage(`Применено: ${proposal.code} ${proposal.name}`);
    } catch (err) {
      setError(parseApiError(err, "Не удалось применить сдвиг"));
    } finally {
      setBusy(false);
    }
  };

  const applyAll = async () => {
    if (!onApplyProposals || !proposals?.proposals.length) return;
    setBusy(true);
    setError("");
    try {
      const batch = await onApplyProposals(proposals.proposals);
      setUndoBatch(batch);
      setProposals((prev) => (prev ? { ...prev, proposals: [] } : prev));
      setMessage(`Применено всех сдвигов: ${batch.items.length}`);
    } catch (err) {
      setError(parseApiError(err, "Не удалось применить сдвиги"));
    } finally {
      setBusy(false);
    }
  };

  const undo = async () => {
    if (!onUndoLeveling || !undoBatch) return;
    setBusy(true);
    setError("");
    try {
      await onUndoLeveling(undoBatch);
      setUndoBatch(null);
      setMessage("Сдвиги отменены (undo)");
    } catch (err) {
      setError(parseApiError(err, "Не удалось отменить сдвиги"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-2">
      {overloadedCount > 0 && (
        <div className="flex flex-wrap items-center gap-3 text-sm text-accent">
          <p role="status">
            <TermHint term="capacity">Capacity</TermHint>: {overloadedCount} задач с
            перегруженным исполнителем на текущей неделе.
          </p>
          {onProposeLeveling && (
            <button
              type="button"
              disabled={busy}
              onClick={() => void propose()}
              className="rounded-lg bg-primary px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-60"
            >
              {busy ? "…" : "Предложить сдвиг"}
            </button>
          )}
        </div>
      )}
      {message && (
        <p className="text-sm text-secondary" role="status">
          {message}
        </p>
      )}
      {error && <p className="text-sm text-primary">{error}</p>}
      {proposals && proposals.proposals.length > 0 && (
        <div className="space-y-2">
          <div className="flex flex-wrap gap-2">
            {onApplyProposals && (
              <button
                type="button"
                disabled={busy}
                onClick={() => void applyAll()}
                className="rounded-lg bg-primary px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-60"
              >
                Применить все
              </button>
            )}
          </div>
          <ul className="space-y-2 rounded-xl border border-border bg-surface p-3 text-sm">
            {proposals.proposals.map((p) => (
              <li
                key={p.activity_id}
                className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-border px-3 py-2"
              >
                <div>
                  <strong>
                    {p.code} {p.name}
                  </strong>
                  <span className="text-text-muted">
                    {" "}
                    · {p.current.start_date}→{p.proposed.start_date} (+
                    {p.shift_days} дн.)
                  </span>
                  <p className="text-xs text-text-muted">{p.reason}</p>
                </div>
                {onApplyProposal && (
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => void applyOne(p)}
                    className="rounded-lg border border-border px-2 py-1 text-xs font-semibold text-primary disabled:opacity-60"
                  >
                    Применить
                  </button>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
      {undoBatch && onUndoLeveling && (
        <button
          type="button"
          disabled={busy}
          onClick={() => void undo()}
          className="rounded-lg border border-border px-3 py-1.5 text-xs font-semibold text-text disabled:opacity-60"
        >
          <GlossaryText text="Undo" /> последнего apply-all
        </button>
      )}
      <div className="gantt-wrapper overflow-x-auto rounded-xl border border-border bg-surface p-4">
        <div ref={containerRef} />
      </div>
    </div>
  );
}
