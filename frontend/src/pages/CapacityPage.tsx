import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { parseApiError } from "../api/errors";
import type { LevelingProposeResult } from "../api/projects";
import type { CapacityMember } from "../api/workspace";
import { ErrorMessage } from "../components/ErrorMessage";
import { GlossaryText, TermHint } from "../components/TermHint";
import { useWorkspace } from "../context/WorkspaceContext";
import { useProjectsApi } from "../hooks/useProjectsApi";
import { useWorkspaceApi } from "../hooks/useWorkspaceApi";

type MemberProposalBlock = {
  projectId: number;
  projectName: string;
  result: LevelingProposeResult;
};

type UndoBatch = {
  projectId: number;
  items: Array<{
    activity_id: number;
    start_date: string | null;
    end_date: string | null;
    duration_days?: number;
  }>;
};

export function CapacityPage() {
  const workspaceApi = useWorkspaceApi();
  const projectsApi = useProjectsApi();
  const { workspaceEpoch, activeWorkspace } = useWorkspace();
  const [members, setMembers] = useState<CapacityMember[]>([]);
  const [weekStart, setWeekStart] = useState("");
  const [weekEnd, setWeekEnd] = useState("");
  const [draftHours, setDraftHours] = useState<Record<number, string>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [savingId, setSavingId] = useState<number | null>(null);
  const [proposingId, setProposingId] = useState<number | null>(null);
  const [applyingKey, setApplyingKey] = useState<string | null>(null);
  const [proposalsByMember, setProposalsByMember] = useState<
    Record<number, MemberProposalBlock[]>
  >({});
  const [undoByMember, setUndoByMember] = useState<Record<number, UndoBatch[]>>(
    {},
  );

  const isOwner = activeWorkspace?.role === "owner";

  const load = useCallback(async () => {
    if (!workspaceApi) {
      return;
    }
    setLoading(true);
    setError("");
    try {
      const data = await workspaceApi.getCapacity();
      setMembers(data.members);
      setWeekStart(data.week_start);
      setWeekEnd(data.week_end);
      setDraftHours(
        Object.fromEntries(
          data.members.map((member) => [
            member.user_id,
            String(member.capacity_hours),
          ]),
        ),
      );
    } catch (err) {
      setError(parseApiError(err, "Не удалось загрузить capacity"));
    } finally {
      setLoading(false);
    }
  }, [workspaceApi]);

  useEffect(() => {
    void load();
  }, [load, workspaceEpoch, activeWorkspace?.id]);

  const handleSave = async (userId: number) => {
    if (!workspaceApi) {
      return;
    }
    const raw = draftHours[userId];
    const hours = Number(raw);
    if (!Number.isFinite(hours) || hours < 0) {
      setError("Укажите корректное число часов");
      return;
    }
    setSavingId(userId);
    setError("");
    try {
      await workspaceApi.setCapacity(userId, hours);
      await load();
    } catch (err) {
      setError(parseApiError(err, "Не удалось сохранить capacity"));
    } finally {
      setSavingId(null);
    }
  };

  const handlePropose = async (member: CapacityMember) => {
    if (!projectsApi) return;
    const byProject = new Map<number, string>();
    for (const a of member.assignments) {
      if (a.project_id) {
        byProject.set(a.project_id, a.project_name || `Project #${a.project_id}`);
      }
    }
    if (byProject.size === 0) {
      setError("Нет назначений с project_id для leveling");
      return;
    }
    setProposingId(member.user_id);
    setError("");
    setMessage("");
    try {
      const blocks: MemberProposalBlock[] = [];
      for (const [projectId, projectName] of byProject) {
        const result = await projectsApi.proposeLeveling(projectId, {
          week_start: weekStart || undefined,
          assignee_id: member.user_id,
          max_shift_days: 14,
        });
        if (result.proposals.length > 0) {
          blocks.push({ projectId, projectName, result });
        }
      }
      setProposalsByMember((prev) => ({
        ...prev,
        [member.user_id]: blocks,
      }));
      if (blocks.length === 0) {
        setError("Нет предложений leveling для этого участника на неделе");
      }
    } catch (err) {
      setError(parseApiError(err, "Не удалось предложить leveling"));
    } finally {
      setProposingId(null);
    }
  };

  const handleApplyAll = async (memberId: number) => {
    if (!projectsApi) return;
    const blocks = proposalsByMember[memberId] ?? [];
    if (blocks.length === 0) return;
    setApplyingKey(`all-${memberId}`);
    setError("");
    try {
      const undoBatches: UndoBatch[] = [];
      for (const block of blocks) {
        const result = await projectsApi.applyLeveling(
          block.projectId,
          block.result.proposals,
        );
        if (result.batch?.items?.length) {
          undoBatches.push({
            projectId: block.projectId,
            items: result.batch.items,
          });
        }
      }
      setUndoByMember((prev) => ({ ...prev, [memberId]: undoBatches }));
      setProposalsByMember((prev) => ({ ...prev, [memberId]: [] }));
      setMessage("Leveling применён — capacity обновлён");
      await load();
    } catch (err) {
      setError(parseApiError(err, "Не удалось применить leveling"));
    } finally {
      setApplyingKey(null);
    }
  };

  const handleApplyBlock = async (memberId: number, projectId: number) => {
    if (!projectsApi) return;
    const blocks = proposalsByMember[memberId] ?? [];
    const block = blocks.find((b) => b.projectId === projectId);
    if (!block) return;
    setApplyingKey(`${memberId}-${projectId}`);
    setError("");
    try {
      const result = await projectsApi.applyLeveling(
        block.projectId,
        block.result.proposals,
      );
      if (result.batch?.items?.length) {
        setUndoByMember((prev) => ({
          ...prev,
          [memberId]: [
            ...(prev[memberId] ?? []),
            { projectId: block.projectId, items: result.batch.items },
          ],
        }));
      }
      setProposalsByMember((prev) => ({
        ...prev,
        [memberId]: (prev[memberId] ?? []).filter((b) => b.projectId !== projectId),
      }));
      setMessage(`Leveling применён для проекта #${projectId}`);
      await load();
    } catch (err) {
      setError(parseApiError(err, "Не удалось применить leveling"));
    } finally {
      setApplyingKey(null);
    }
  };

  const handleUndo = async (memberId: number) => {
    if (!projectsApi) return;
    const batches = undoByMember[memberId] ?? [];
    if (batches.length === 0) return;
    setApplyingKey(`undo-${memberId}`);
    setError("");
    try {
      for (const batch of batches) {
        await projectsApi.undoLeveling(batch.projectId, batch.items);
      }
      setUndoByMember((prev) => ({ ...prev, [memberId]: [] }));
      setMessage("Leveling откатан");
      await load();
    } catch (err) {
      setError(parseApiError(err, "Не удалось откатить leveling"));
    } finally {
      setApplyingKey(null);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-text">
          <TermHint term="capacity">Capacity</TermHint>
        </h1>
        <p className="mt-2 text-text-muted">
          Неделя: {weekStart || "—"} — {weekEnd || "—"}
          {isOwner ? " · редактирование доступно владельцу" : ""}
        </p>
      </div>

      <ErrorMessage message={error} onDismiss={() => setError("")} />
      {message && (
        <p className="text-sm text-secondary" role="status">
          {message}
        </p>
      )}

      {loading && <p className="text-sm text-text-muted">Загрузка...</p>}

      {!loading && (
        <div className="overflow-x-auto rounded-xl border border-border bg-surface">
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-border bg-cream text-text-muted">
              <tr>
                <th className="px-4 py-3 font-medium">Участник</th>
                <th className="px-4 py-3 font-medium">Роль</th>
                <th className="px-4 py-3 font-medium">Capacity (ч/нед)</th>
                <th className="px-4 py-3 font-medium">Выделено</th>
                <th className="px-4 py-3 font-medium">
                  <GlossaryText text="Utilization" />
                </th>
                <th className="px-4 py-3 font-medium" />
              </tr>
            </thead>
            <tbody>
              {members.length === 0 && (
                <tr>
                  <td
                    colSpan={6}
                    className="px-4 py-6 text-center text-text-muted"
                  >
                    Нет участников
                  </td>
                </tr>
              )}
              {members.map((member) => {
                const overloaded =
                  member.utilization != null && member.utilization > 1;
                const blocks = proposalsByMember[member.user_id] ?? [];
                const undoBatches = undoByMember[member.user_id] ?? [];
                return (
                  <tr
                    key={member.user_id}
                    className="border-b border-border align-top"
                  >
                    <td className="px-4 py-3">
                      <p className="font-medium text-text">{member.name}</p>
                      <p className="text-xs text-text-muted">{member.email}</p>
                      {blocks.length > 0 && (
                        <ul className="mt-2 space-y-2 text-xs text-text-muted">
                          {blocks.map((block) => (
                            <li
                              key={block.projectId}
                              className="rounded border border-border bg-cream/60 px-2 py-1.5"
                            >
                              <div className="flex flex-wrap items-center justify-between gap-2">
                                <span>
                                  {block.projectName}:{" "}
                                  {block.result.proposals.length} сдвиг(ов)
                                </span>
                                <span className="flex gap-2">
                                  <Link
                                    className="text-primary hover:underline"
                                    to={`/projects/${block.projectId}?tab=gantt`}
                                  >
                                    Gantt
                                  </Link>
                                  <button
                                    type="button"
                                    className="text-primary hover:underline"
                                    disabled={
                                      applyingKey ===
                                      `${member.user_id}-${block.projectId}`
                                    }
                                    onClick={() =>
                                      void handleApplyBlock(
                                        member.user_id,
                                        block.projectId,
                                      )
                                    }
                                  >
                                    Применить
                                  </button>
                                </span>
                              </div>
                              <ul className="mt-1 space-y-0.5">
                                {block.result.proposals.slice(0, 4).map((p) => (
                                  <li key={p.activity_id}>
                                    {p.code || p.name}: +{p.shift_days}д →{" "}
                                    {p.proposed.start_date}
                                  </li>
                                ))}
                              </ul>
                            </li>
                          ))}
                          <li className="flex flex-wrap gap-2">
                            <button
                              type="button"
                              className="rounded border border-primary px-2 py-1 text-primary"
                              disabled={applyingKey === `all-${member.user_id}`}
                              onClick={() => void handleApplyAll(member.user_id)}
                            >
                              Применить все
                            </button>
                          </li>
                        </ul>
                      )}
                      {undoBatches.length > 0 && (
                        <button
                          type="button"
                          className="mt-2 text-xs text-text-muted hover:text-primary"
                          disabled={applyingKey === `undo-${member.user_id}`}
                          onClick={() => void handleUndo(member.user_id)}
                        >
                          Undo leveling
                        </button>
                      )}
                    </td>
                    <td className="px-4 py-3 text-text-muted">{member.role}</td>
                    <td className="px-4 py-3">
                      <input
                        type="number"
                        min={0}
                        step={1}
                        value={draftHours[member.user_id] ?? ""}
                        onChange={(event) =>
                          setDraftHours((current) => ({
                            ...current,
                            [member.user_id]: event.target.value,
                          }))
                        }
                        className="w-24 rounded-lg border border-border bg-cream px-2 py-1.5 text-sm text-text"
                        aria-label={`Часы для ${member.name}`}
                      />
                    </td>
                    <td className="px-4 py-3 text-text">
                      {member.allocated_hours}
                    </td>
                    <td className="px-4 py-3 text-text">
                      {member.utilization == null
                        ? "—"
                        : `${Math.round(member.utilization * 100)}%`}
                      {overloaded && (
                        <span className="ml-1 text-xs text-primary">overload</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-col gap-1">
                        <button
                          type="button"
                          onClick={() => void handleSave(member.user_id)}
                          disabled={savingId === member.user_id}
                          className="rounded-lg bg-primary px-3 py-1.5 text-xs font-semibold text-white hover:opacity-90 disabled:opacity-50"
                        >
                          {savingId === member.user_id ? "..." : "Сохранить"}
                        </button>
                        {overloaded && projectsApi && (
                          <button
                            type="button"
                            onClick={() => void handlePropose(member)}
                            disabled={proposingId === member.user_id}
                            className="rounded-lg border border-border px-3 py-1.5 text-xs text-text hover:bg-cream disabled:opacity-50"
                          >
                            {proposingId === member.user_id
                              ? "..."
                              : "Предложить leveling"}
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
