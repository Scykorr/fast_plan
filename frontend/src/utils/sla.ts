/** SLA countdown helpers for process UserTask.due_at */

export type SlaState = "ok" | "soon" | "overdue" | "none";

export type SlaInfo = {
  state: SlaState;
  label: string;
  /** Milliseconds until due (negative if overdue). Null if no due. */
  msRemaining: number | null;
};

const SOON_MS = 4 * 60 * 60 * 1000; // 4 hours

function formatDuration(ms: number): string {
  const abs = Math.abs(ms);
  const hours = Math.floor(abs / 3_600_000);
  const minutes = Math.floor((abs % 3_600_000) / 60_000);
  if (hours >= 48) {
    const days = Math.floor(hours / 24);
    return `${days}д`;
  }
  if (hours >= 1) {
    return minutes > 0 ? `${hours}ч ${minutes}м` : `${hours}ч`;
  }
  return `${Math.max(minutes, 1)}м`;
}

export function getSlaInfo(
  dueAt: string | null | undefined,
  now: Date = new Date(),
): SlaInfo {
  if (!dueAt) {
    return { state: "none", label: "без SLA", msRemaining: null };
  }
  const due = new Date(dueAt);
  if (Number.isNaN(due.getTime())) {
    return { state: "none", label: "без SLA", msRemaining: null };
  }
  const msRemaining = due.getTime() - now.getTime();
  if (msRemaining < 0) {
    return {
      state: "overdue",
      label: `просрочено ${formatDuration(msRemaining)}`,
      msRemaining,
    };
  }
  if (msRemaining <= SOON_MS) {
    return {
      state: "soon",
      label: `осталось ${formatDuration(msRemaining)}`,
      msRemaining,
    };
  }
  return {
    state: "ok",
    label: `до ${due.toLocaleString()}`,
    msRemaining,
  };
}

export function slaBadgeClass(state: SlaState): string {
  switch (state) {
    case "overdue":
      return "bg-red-100 text-red-800 border-red-200";
    case "soon":
      return "bg-amber-100 text-amber-900 border-amber-200";
    case "ok":
      return "bg-emerald-50 text-emerald-800 border-emerald-200";
    default:
      return "bg-cream text-text-muted border-border";
  }
}
