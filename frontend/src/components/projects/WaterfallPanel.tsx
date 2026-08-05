import { useCallback, useEffect, useState } from "react";

import { parseApiError } from "../../api/errors";
import type { WaterfallOverview, WaterfallPhase } from "../../api/projects";
import { ErrorMessage } from "../ErrorMessage";
import { useProjectsApi } from "../../hooks/useProjectsApi";

type WaterfallPanelProps = {
  projectId: number;
  methodology: string;
  scheduleLocked: boolean;
  onProjectMetaChange?: (meta: {
    methodology?: string;
    schedule_locked?: boolean;
  }) => void;
};

const GATE_LABEL: Record<string, string> = {
  locked: "Заблокирована",
  open: "Открыта",
  in_review: "На ревью",
  passed: "Пройдена",
  failed: "Отклонена",
};

export function WaterfallPanel({
  projectId,
  methodology,
  scheduleLocked,
  onProjectMetaChange,
}: WaterfallPanelProps) {
  const api = useProjectsApi();
  const [data, setData] = useState<WaterfallOverview | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [comment, setComment] = useState("");
  const [busy, setBusy] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editTitle, setEditTitle] = useState("");

  const locked = scheduleLocked || Boolean(data?.schedule_locked);

  const load = useCallback(async () => {
    if (!api) return;
    try {
      const overview = await api.getWaterfall(projectId);
      setData(overview);
      onProjectMetaChange?.({
        methodology: overview.methodology,
        schedule_locked: overview.schedule_locked,
      });
    } catch (err) {
      setError(parseApiError(err));
    }
  }, [api, projectId]); // onProjectMetaChange is best-effort parent sync

  useEffect(() => {
    void load();
  }, [load]);

  const seed = async (replace: boolean) => {
    if (!api) return;
    setBusy(true);
    setError("");
    try {
      await api.seedWaterfall(projectId, {
        replace,
        set_methodology: true,
      });
      setMessage(
        replace
          ? "Фазы Waterfall пересозданы"
          : "Сидированы фазы SDLC (Requirements → Maintenance)",
      );
      await load();
    } catch (err) {
      setError(parseApiError(err));
    } finally {
      setBusy(false);
    }
  };

  const decide = async (phase: WaterfallPhase, decision: "pass" | "fail") => {
    if (!api) return;
    setBusy(true);
    setError("");
    try {
      const checklist = (data?.default_checklist || []).map((item) => ({
        ...item,
        done: decision === "pass",
      }));
      const result = await api.decidePhaseGate(projectId, {
        wbs_phase_node_id: phase.id,
        decision,
        comment,
        checklist,
        create_baseline: decision === "pass",
        lock_schedule: decision === "pass",
      });
      setComment("");
      setMessage(
        decision === "pass"
          ? `Гейт «${phase.title}» пройден` +
              (result.schedule_locked ? " · schedule locked" : "")
          : `Гейт «${phase.title}» отклонён — фаза открыта на доработку`,
      );
      await load();
    } catch (err) {
      setError(parseApiError(err));
    } finally {
      setBusy(false);
    }
  };

  const addPhase = async () => {
    if (!api || !newTitle.trim()) return;
    setBusy(true);
    setError("");
    try {
      const created = await api.addWaterfallPhase(projectId, {
        title: newTitle.trim(),
      });
      setNewTitle("");
      setMessage(`Фаза «${created.title}» добавлена`);
      await load();
    } catch (err) {
      setError(parseApiError(err));
    } finally {
      setBusy(false);
    }
  };

  const saveRename = async (phaseId: number) => {
    if (!api || !editTitle.trim()) return;
    setBusy(true);
    setError("");
    try {
      const updated = await api.renameWaterfallPhase(
        projectId,
        phaseId,
        editTitle.trim(),
      );
      setEditingId(null);
      setMessage(`Фаза переименована в «${updated.title}»`);
      await load();
    } catch (err) {
      setError(parseApiError(err));
    } finally {
      setBusy(false);
    }
  };

  const removePhase = async (phase: WaterfallPhase) => {
    if (!api) return;
    if (
      !window.confirm(
        `Удалить фазу «${phase.title}» и все дочерние работы?`,
      )
    ) {
      return;
    }
    setBusy(true);
    setError("");
    try {
      await api.deleteWaterfallPhase(projectId, phase.id);
      setMessage(`Фаза «${phase.title}» удалена`);
      await load();
    } catch (err) {
      setError(parseApiError(err));
    } finally {
      setBusy(false);
    }
  };

  const phases = data?.phases || [];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-text">Waterfall / Predictive</h2>
          <p className="mt-1 text-sm text-text-muted">
            Фазы можно добавлять, переименовывать и удалять. После pass — baseline и
            заморозка расписания; структурные правки (add/delete) — через Change Request.
          </p>
          <p className="mt-2 text-xs text-text-muted">
            methodology: <span className="text-text">{methodology}</span>
            {locked ? (
              <span className="ml-2 rounded border border-amber-500/40 bg-amber-500/10 px-1.5 py-0.5 text-amber-800">
                schedule locked
              </span>
            ) : null}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            disabled={busy || phases.length > 0}
            onClick={() => void seed(false)}
            className="rounded-lg bg-primary px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-50"
          >
            Сидировать SDLC
          </button>
          {phases.length > 0 && (
            <button
              type="button"
              disabled={busy || locked}
              onClick={() => void seed(true)}
              className="rounded-lg border border-border px-3 py-1.5 text-sm disabled:opacity-50"
              title={locked ? "Сначала approve Change Request" : undefined}
            >
              Пересоздать
            </button>
          )}
        </div>
      </div>

      <ErrorMessage message={error} onDismiss={() => setError("")} />
      {message && (
        <p className="text-sm text-secondary" role="status">
          {message}
        </p>
      )}

      <div className="flex flex-wrap items-end gap-2 rounded-xl border border-border bg-cream/40 p-3">
        <label className="min-w-[12rem] flex-1 text-xs text-text-muted">
          Новая фаза
          <input
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
            disabled={busy || locked}
            placeholder="Например: Deployment"
            className="mt-1 w-full rounded-lg border border-border bg-surface px-3 py-1.5 text-sm text-text disabled:opacity-50"
          />
        </label>
        <button
          type="button"
          disabled={busy || locked || !newTitle.trim()}
          onClick={() => void addPhase()}
          className="rounded-lg bg-primary px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-50"
        >
          Добавить
        </button>
      </div>

      {phases.length === 0 ? (
        <p className="text-sm text-text-muted">
          Фаз ещё нет. Сидируйте классический SDLC или добавьте свою первую фазу.
        </p>
      ) : (
        <ol className="space-y-3">
          {phases.map((phase, index) => {
            const canDecide =
              phase.gate_status === "open" || phase.gate_status === "in_review";
            const isEditing = editingId === phase.id;
            return (
              <li
                key={phase.id}
                className="rounded-xl border border-border bg-surface p-4"
              >
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div className="min-w-0 flex-1">
                    {isEditing ? (
                      <div className="flex flex-wrap items-center gap-2">
                        <input
                          value={editTitle}
                          onChange={(e) => setEditTitle(e.target.value)}
                          className="min-w-[10rem] flex-1 rounded-lg border border-border bg-cream px-2 py-1 text-sm"
                          autoFocus
                        />
                        <button
                          type="button"
                          disabled={busy || !editTitle.trim()}
                          onClick={() => void saveRename(phase.id)}
                          className="rounded-lg bg-primary px-2 py-1 text-xs font-semibold text-white"
                        >
                          Сохранить
                        </button>
                        <button
                          type="button"
                          disabled={busy}
                          onClick={() => setEditingId(null)}
                          className="rounded-lg border border-border px-2 py-1 text-xs"
                        >
                          Отмена
                        </button>
                      </div>
                    ) : (
                      <p className="font-semibold text-text">
                        {index + 1}. {phase.title}
                        <span className="ml-2 text-xs font-normal text-text-muted">
                          {phase.phase_key || "custom"} · {phase.code}
                        </span>
                      </p>
                    )}
                    <p className="mt-1 text-xs text-text-muted">
                      {GATE_LABEL[phase.gate_status || ""] || phase.gate_status || "—"}
                      {phase.start_date
                        ? ` · ${phase.start_date} → ${phase.end_date || "…"}`
                        : ""}
                      {` · progress ${phase.progress}%`}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {!isEditing && (
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() => {
                          setEditingId(phase.id);
                          setEditTitle(phase.title);
                        }}
                        className="rounded-lg border border-border px-2 py-1 text-xs"
                      >
                        Переименовать
                      </button>
                    )}
                    <button
                      type="button"
                      disabled={busy || locked}
                      onClick={() => void removePhase(phase)}
                      className="rounded-lg border border-border px-2 py-1 text-xs text-danger disabled:opacity-50"
                      title={locked ? "Сначала approve Change Request" : undefined}
                    >
                      Удалить
                    </button>
                    {canDecide && (
                      <>
                        <button
                          type="button"
                          disabled={busy}
                          onClick={() => void decide(phase, "pass")}
                          className="rounded-lg bg-primary px-3 py-1.5 text-xs font-semibold text-white"
                        >
                          Pass (go)
                        </button>
                        <button
                          type="button"
                          disabled={busy}
                          onClick={() => void decide(phase, "fail")}
                          className="rounded-lg border border-border px-3 py-1.5 text-xs"
                        >
                          Fail (no-go)
                        </button>
                      </>
                    )}
                  </div>
                </div>
              </li>
            );
          })}
        </ol>
      )}

      {phases.some(
        (p) => p.gate_status === "open" || p.gate_status === "in_review",
      ) && (
        <label className="block text-sm text-text-muted">
          Комментарий к решению
          <textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            rows={2}
            className="mt-1 w-full rounded-lg border border-border bg-cream px-3 py-2 text-sm text-text"
            placeholder="Обоснование go/no-go…"
          />
        </label>
      )}

      {(data?.gates?.length || 0) > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-text">История гейтов</h3>
          <ul className="mt-2 space-y-2">
            {data!.gates.map((gate) => (
              <li
                key={gate.id}
                className="rounded-lg border border-border bg-cream/50 px-3 py-2 text-xs text-text-muted"
              >
                <span className="font-medium text-text">{gate.phase_title}</span>
                {" · "}
                {gate.decision}
                {gate.decided_by_email ? ` · ${gate.decided_by_email}` : ""}
                {gate.baseline_name ? ` · baseline «${gate.baseline_name}»` : ""}
                {gate.comment ? ` — ${gate.comment}` : ""}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
