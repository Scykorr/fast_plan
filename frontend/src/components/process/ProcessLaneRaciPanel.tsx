import { useCallback, useEffect, useState } from "react";

import { parseApiError } from "../../api/errors";
import type { ProcessLane, ProcessLaneRole } from "../../api/process";
import { useProcessApi } from "../../hooks/useProcessApi";

const ROLE_OPTIONS = [
  { value: "", label: "— роль —" },
  { value: "owner", label: "owner" },
  { value: "editor", label: "editor" },
  { value: "viewer", label: "viewer" },
  { value: "sales", label: "crm:sales" },
  { value: "manager", label: "crm:manager" },
];

type ProcessLaneRaciPanelProps = {
  definitionId: number;
};

export function ProcessLaneRaciPanel({ definitionId }: ProcessLaneRaciPanelProps) {
  const api = useProcessApi();
  const [lanes, setLanes] = useState<ProcessLane[]>([]);
  const [roles, setRoles] = useState<ProcessLaneRole[]>([]);
  const [error, setError] = useState("");
  const [draftRole, setDraftRole] = useState<Record<string, string>>({});
  const [draftRaci, setDraftRaci] = useState<Record<string, string>>({});
  const [manualLaneId, setManualLaneId] = useState("");
  const [manualLaneName, setManualLaneName] = useState("");

  const load = useCallback(async () => {
    if (!api) return;
    try {
      const [laneList, roleList] = await Promise.all([
        api.listLanes(definitionId),
        api.listLaneRoles(definitionId),
      ]);
      setLanes(laneList);
      setRoles(roleList);
      const nextDraft: Record<string, string> = {};
      const nextRaci: Record<string, string> = {};
      for (const role of roleList) {
        if (role.raci_type === "R" || !nextDraft[role.lane_id]) {
          nextDraft[role.lane_id] = role.role_key;
          nextRaci[role.lane_id] = role.raci_type;
        }
      }
      setDraftRole(nextDraft);
      setDraftRaci(nextRaci);
      setError("");
    } catch (err) {
      setError(parseApiError(err));
    }
  }, [api, definitionId]);

  useEffect(() => {
    void load();
  }, [load]);

  const saveLane = async (laneId: string, laneName: string) => {
    if (!api) return;
    try {
      await api.upsertLaneRole(definitionId, {
        lane_id: laneId,
        lane_name: laneName,
        raci_type: draftRaci[laneId] || "R",
        role_key: draftRole[laneId] || "",
      });
      await load();
    } catch (err) {
      setError(parseApiError(err));
    }
  };

  const removeRole = async (roleId: number) => {
    if (!api) return;
    try {
      await api.deleteLaneRole(roleId);
      await load();
    } catch (err) {
      setError(parseApiError(err));
    }
  };

  const displayLanes =
    lanes.length > 0
      ? lanes
      : roles.map((r) => ({
          lane_id: r.lane_id,
          lane_name: r.lane_name || r.lane_id,
          flow_node_refs: [] as string[],
        }));

  return (
    <div className="rounded-xl border border-border bg-cream/40 p-3 text-sm">
      <h3 className="font-semibold text-text">Process RACI (lane → роль)</h3>
      <p className="mt-1 text-xs text-text-muted">
        Сопоставьте BPMN lane с workspace/crm ролью. Если в XML нет lanes —
        добавьте вручную по id.
      </p>
      {error && <p className="mt-2 text-xs text-red-700">{error}</p>}
      <ul className="mt-3 space-y-2">
        {displayLanes.map((lane) => {
          const existing = roles.filter((r) => r.lane_id === lane.lane_id);
          return (
            <li
              key={lane.lane_id}
              className="flex flex-wrap items-end gap-2 rounded border border-border bg-surface px-2 py-2"
            >
              <div className="min-w-[8rem] flex-1">
                <p className="font-medium text-text">{lane.lane_name}</p>
                <p className="text-[11px] text-text-muted">{lane.lane_id}</p>
              </div>
              <select
                className="rounded border border-border bg-cream px-2 py-1 text-xs"
                value={draftRaci[lane.lane_id] || "R"}
                onChange={(e) =>
                  setDraftRaci((prev) => ({
                    ...prev,
                    [lane.lane_id]: e.target.value,
                  }))
                }
              >
                {["R", "A", "C", "I"].map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
              <select
                className="rounded border border-border bg-cream px-2 py-1 text-xs"
                value={draftRole[lane.lane_id] || ""}
                onChange={(e) =>
                  setDraftRole((prev) => ({
                    ...prev,
                    [lane.lane_id]: e.target.value,
                  }))
                }
              >
                {ROLE_OPTIONS.map((o) => (
                  <option key={o.value || "empty"} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
              <button
                type="button"
                className="rounded bg-primary px-2 py-1 text-xs font-semibold text-white"
                onClick={() => void saveLane(lane.lane_id, lane.lane_name)}
              >
                Сохранить
              </button>
              {existing.map((r) => (
                <button
                  key={r.id}
                  type="button"
                  className="text-xs text-text-muted hover:text-red-700"
                  onClick={() => void removeRole(r.id)}
                >
                  удалить {r.raci_type}
                </button>
              ))}
            </li>
          );
        })}
        {displayLanes.length === 0 && (
          <li className="text-xs text-text-muted">
            Lanes в BPMN не найдены — добавьте mapping вручную ниже.
          </li>
        )}
      </ul>
      <div className="mt-3 flex flex-wrap gap-2">
        <input
          className="rounded border border-border bg-cream px-2 py-1 text-xs"
          placeholder="lane_id"
          value={manualLaneId}
          onChange={(e) => setManualLaneId(e.target.value)}
        />
        <input
          className="rounded border border-border bg-cream px-2 py-1 text-xs"
          placeholder="lane name"
          value={manualLaneName}
          onChange={(e) => setManualLaneName(e.target.value)}
        />
        <button
          type="button"
          className="rounded border border-border px-2 py-1 text-xs"
          onClick={() => {
            if (!manualLaneId.trim()) return;
            void saveLane(manualLaneId.trim(), manualLaneName.trim() || manualLaneId.trim());
            setManualLaneId("");
            setManualLaneName("");
          }}
        >
          + lane mapping
        </button>
      </div>
    </div>
  );
}
