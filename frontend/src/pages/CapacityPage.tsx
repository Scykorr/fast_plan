import { useCallback, useEffect, useState } from "react";

import { parseApiError } from "../api/errors";
import type { CapacityMember } from "../api/workspace";
import { ErrorMessage } from "../components/ErrorMessage";
import { useWorkspace } from "../context/WorkspaceContext";
import { useWorkspaceApi } from "../hooks/useWorkspaceApi";

export function CapacityPage() {
  const workspaceApi = useWorkspaceApi();
  const { workspaceEpoch, activeWorkspace } = useWorkspace();
  const [members, setMembers] = useState<CapacityMember[]>([]);
  const [weekStart, setWeekStart] = useState("");
  const [weekEnd, setWeekEnd] = useState("");
  const [draftHours, setDraftHours] = useState<Record<number, string>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [savingId, setSavingId] = useState<number | null>(null);

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

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-text">Capacity</h1>
        <p className="mt-2 text-text-muted">
          Неделя: {weekStart || "—"} — {weekEnd || "—"}
          {isOwner ? " · редактирование доступно владельцу" : ""}
        </p>
      </div>

      <ErrorMessage message={error} onDismiss={() => setError("")} />

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
                <th className="px-4 py-3 font-medium">Utilization</th>
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
              {members.map((member) => (
                <tr key={member.user_id} className="border-b border-border">
                  <td className="px-4 py-3">
                    <p className="font-medium text-text">{member.name}</p>
                    <p className="text-xs text-text-muted">{member.email}</p>
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
                  </td>
                  <td className="px-4 py-3">
                    <button
                      type="button"
                      onClick={() => void handleSave(member.user_id)}
                      disabled={savingId === member.user_id}
                      className="rounded-lg bg-primary px-3 py-1.5 text-xs font-semibold text-white hover:opacity-90 disabled:opacity-50"
                    >
                      {savingId === member.user_id ? "..." : "Сохранить"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
