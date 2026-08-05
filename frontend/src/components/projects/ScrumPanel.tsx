import { useCallback, useEffect, useMemo, useState } from "react";

import { parseApiError } from "../../api/errors";
import type { ProductBacklogItem, ScrumSprint } from "../../api/scrum";
import { createScrumApi } from "../../api/scrum";
import type { WorkspaceMember } from "../../api/workspace";
import { AssigneeSelect } from "../AssigneeSelect";
import { ErrorMessage } from "../ErrorMessage";

type ScrumPanelProps = {
  projectId: number;
  members: WorkspaceMember[];
};

const BOARD_COLS: Array<{ id: ProductBacklogItem["status"]; label: string }> = [
  { id: "todo", label: "To Do" },
  { id: "in_progress", label: "In Progress" },
  { id: "done", label: "Done" },
];

export function ScrumPanel({ projectId, members }: ScrumPanelProps) {
  const api = useMemo(() => createScrumApi(), []);
  const [subTab, setSubTab] = useState<"backlog" | "board" | "burndown">(
    "backlog",
  );
  const [pbis, setPbis] = useState<ProductBacklogItem[]>([]);
  const [sprints, setSprints] = useState<ScrumSprint[]>([]);
  const [activeSprintId, setActiveSprintId] = useState<number | null>(null);
  const [sprintItems, setSprintItems] = useState<ProductBacklogItem[]>([]);
  const [burndown, setBurndown] = useState<
    Array<{ date: string; remaining: number | null; ideal: number }>
  >([]);
  const [error, setError] = useState("");
  const [title, setTitle] = useState("");
  const [points, setPoints] = useState("3");
  const [assigneeId, setAssigneeId] = useState<number | null>(null);
  const [sprintName, setSprintName] = useState("");
  const [sprintGoal, setSprintGoal] = useState("");
  const [startsOn, setStartsOn] = useState("");
  const [endsOn, setEndsOn] = useState("");
  const [selectedIds, setSelectedIds] = useState<number[]>([]);

  const load = useCallback(async () => {
    try {
      const [backlog, sprintList] = await Promise.all([
        api.listBacklog(projectId),
        api.listSprints(projectId),
      ]);
      setPbis(backlog);
      setSprints(sprintList);
      const active =
        sprintList.find((s) => s.status === "active") || sprintList[0] || null;
      setActiveSprintId((prev) => prev ?? active?.id ?? null);
      setError("");
    } catch (err) {
      setError(parseApiError(err));
    }
  }, [api, projectId]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!activeSprintId) {
      setSprintItems([]);
      setBurndown([]);
      return;
    }
    void (async () => {
      try {
        const [items, burn] = await Promise.all([
          api.sprintBacklog(activeSprintId),
          api.burndown(activeSprintId),
        ]);
        setSprintItems(items);
        setBurndown(burn.burndown);
      } catch (err) {
        setError(parseApiError(err));
      }
    })();
  }, [api, activeSprintId, pbis]);

  const productBacklog = pbis.filter((p) => p.sprint_id == null);

  const addPbi = async () => {
    if (!title.trim()) return;
    try {
      await api.createPbi(projectId, {
        title: title.trim(),
        story_points: points ? Number(points) : null,
        assignee_id: assigneeId,
      });
      setTitle("");
      await load();
    } catch (err) {
      setError(parseApiError(err));
    }
  };

  const createSprint = async () => {
    if (!sprintName.trim()) return;
    try {
      const sprint = await api.createSprint(projectId, {
        name: sprintName.trim(),
        goal: sprintGoal,
        starts_on: startsOn || null,
        ends_on: endsOn || null,
      });
      setSprintName("");
      setSprintGoal("");
      setActiveSprintId(sprint.id);
      await load();
    } catch (err) {
      setError(parseApiError(err));
    }
  };

  const commitSelected = async () => {
    if (!activeSprintId || selectedIds.length === 0) return;
    try {
      await api.commitToSprint(activeSprintId, selectedIds);
      setSelectedIds([]);
      await load();
    } catch (err) {
      setError(parseApiError(err));
    }
  };

  const moveStatus = async (pbiId: number, status: string) => {
    try {
      await api.updatePbi(pbiId, { status });
      await load();
    } catch (err) {
      setError(parseApiError(err));
    }
  };

  const assignPbi = async (pbiId: number, userId: number | null) => {
    try {
      await api.updatePbi(pbiId, { assignee_id: userId });
      await load();
    } catch (err) {
      setError(parseApiError(err));
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="text-lg font-semibold text-text">Scrum</h2>
          <p className="text-sm text-text-muted">
            Product Backlog → Sprint Backlog → Board (To Do / In Progress /
            Done) · story-point burndown (Scrum Guide).
          </p>
        </div>
        <div className="flex gap-1">
          {(
            [
              ["backlog", "Backlog"],
              ["board", "Sprint board"],
              ["burndown", "Burndown"],
            ] as const
          ).map(([id, label]) => (
            <button
              key={id}
              type="button"
              onClick={() => setSubTab(id)}
              className={[
                "rounded-lg border px-3 py-1.5 text-xs font-medium",
                subTab === id
                  ? "border-primary bg-primary/10 text-primary"
                  : "border-border text-text-muted",
              ].join(" ")}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      <ErrorMessage message={error} onDismiss={() => setError("")} />

      <div className="flex flex-wrap items-end gap-2 rounded-xl border border-border bg-surface p-3 text-sm">
        <label className="text-xs text-text-muted">
          Sprint
          <select
            className="mt-1 block rounded-lg border border-border bg-cream px-2 py-1.5"
            value={activeSprintId ?? ""}
            onChange={(e) =>
              setActiveSprintId(e.target.value ? Number(e.target.value) : null)
            }
          >
            <option value="">—</option>
            {sprints.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name} ({s.status}) · {s.remaining_points}/{s.committed_points}{" "}
                SP
              </option>
            ))}
          </select>
        </label>
        {activeSprintId && (
          <>
            <button
              type="button"
              className="rounded-lg border border-border px-3 py-1.5 text-xs"
              onClick={() =>
                void api.activateSprint(activeSprintId).then(load)
              }
            >
              Activate
            </button>
            <button
              type="button"
              className="rounded-lg border border-border px-3 py-1.5 text-xs"
              onClick={() =>
                void api.completeSprint(activeSprintId).then(load)
              }
            >
              Complete
            </button>
          </>
        )}
      </div>

      {subTab === "backlog" && (
        <div className="space-y-4">
          <form
            className="grid gap-2 rounded-xl border border-border bg-surface p-4 sm:grid-cols-4"
            onSubmit={(e) => {
              e.preventDefault();
              void addPbi();
            }}
          >
            <input
              className="rounded-lg border border-border bg-cream px-3 py-2 text-sm sm:col-span-2"
              placeholder="PBI / user story…"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
            <input
              type="number"
              min={0}
              className="rounded-lg border border-border bg-cream px-3 py-2 text-sm"
              placeholder="SP"
              value={points}
              onChange={(e) => setPoints(e.target.value)}
            />
            <AssigneeSelect
              members={members}
              value={assigneeId}
              onChange={setAssigneeId}
              className="rounded-lg border border-border bg-cream px-3 py-2 text-sm"
            />
            <button
              type="submit"
              className="rounded-lg bg-primary px-3 py-2 text-sm font-semibold text-white sm:col-span-4 sm:w-fit"
            >
              Добавить в Product Backlog
            </button>
          </form>

          <div className="grid gap-2 rounded-xl border border-border bg-surface p-4 sm:grid-cols-4">
            <input
              className="rounded-lg border border-border bg-cream px-3 py-2 text-sm"
              placeholder="Sprint name"
              value={sprintName}
              onChange={(e) => setSprintName(e.target.value)}
            />
            <input
              className="rounded-lg border border-border bg-cream px-3 py-2 text-sm sm:col-span-2"
              placeholder="Sprint Goal"
              value={sprintGoal}
              onChange={(e) => setSprintGoal(e.target.value)}
            />
            <button
              type="button"
              className="rounded-lg border border-border px-3 py-2 text-sm"
              onClick={() => void createSprint()}
            >
              Создать sprint
            </button>
            <input
              type="date"
              className="rounded-lg border border-border bg-cream px-3 py-2 text-sm"
              value={startsOn}
              onChange={(e) => setStartsOn(e.target.value)}
            />
            <input
              type="date"
              className="rounded-lg border border-border bg-cream px-3 py-2 text-sm"
              value={endsOn}
              onChange={(e) => setEndsOn(e.target.value)}
            />
          </div>

          <div className="rounded-xl border border-border bg-surface p-4">
            <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
              <h3 className="font-semibold text-text">Product Backlog</h3>
              <button
                type="button"
                className="rounded-lg bg-secondary px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-50"
                disabled={!activeSprintId || selectedIds.length === 0}
                onClick={() => void commitSelected()}
              >
                Commit to sprint ({selectedIds.length})
              </button>
            </div>
            <ul className="space-y-2 text-sm">
              {productBacklog.map((p) => (
                <li
                  key={p.id}
                  className="flex flex-wrap items-center gap-2 rounded border border-border px-2 py-1.5"
                >
                  <input
                    type="checkbox"
                    checked={selectedIds.includes(p.id)}
                    onChange={(e) =>
                      setSelectedIds((prev) =>
                        e.target.checked
                          ? [...prev, p.id]
                          : prev.filter((id) => id !== p.id),
                      )
                    }
                  />
                  <span className="flex-1 font-medium text-text">{p.title}</span>
                  <span className="text-xs text-text-muted">
                    {p.story_points ?? "—"} SP
                  </span>
                  <AssigneeSelect
                    members={members}
                    value={p.assignee_id}
                    onChange={(uid) => void assignPbi(p.id, uid)}
                    className="rounded border border-border bg-cream px-2 py-1 text-xs"
                  />
                  <button
                    type="button"
                    className="text-xs text-text-muted hover:text-red-700"
                    onClick={() => void api.deletePbi(p.id).then(load)}
                  >
                    ×
                  </button>
                </li>
              ))}
              {productBacklog.length === 0 && (
                <li className="text-text-muted">Product Backlog пуст</li>
              )}
            </ul>
          </div>
        </div>
      )}

      {subTab === "board" && (
        <div className="grid gap-3 md:grid-cols-3">
          {BOARD_COLS.map((col) => (
            <div
              key={col.id}
              className="rounded-xl border border-border bg-surface p-3"
            >
              <h3 className="mb-2 text-sm font-semibold text-text">{col.label}</h3>
              <ul className="space-y-2">
                {sprintItems
                  .filter((p) => p.status === col.id)
                  .map((p) => (
                    <li
                      key={p.id}
                      className="rounded-lg border border-border bg-cream/50 p-2 text-sm"
                    >
                      <p className="font-medium text-text">{p.title}</p>
                      <p className="text-xs text-text-muted">
                        {p.story_points ?? "—"} SP
                        {p.assignee_name ? ` · ${p.assignee_name}` : ""}
                      </p>
                      <div className="mt-2 flex flex-wrap gap-1">
                        {BOARD_COLS.filter((c) => c.id !== col.id).map((c) => (
                          <button
                            key={c.id}
                            type="button"
                            className="rounded border border-border px-1.5 py-0.5 text-[10px]"
                            onClick={() => void moveStatus(p.id, c.id)}
                          >
                            → {c.label}
                          </button>
                        ))}
                      </div>
                      <AssigneeSelect
                        members={members}
                        value={p.assignee_id}
                        onChange={(uid) => void assignPbi(p.id, uid)}
                        className="mt-2 w-full rounded border border-border bg-cream px-2 py-1 text-xs"
                      />
                    </li>
                  ))}
              </ul>
            </div>
          ))}
          {!activeSprintId && (
            <p className="text-sm text-text-muted md:col-span-3">
              Создайте и выберите sprint, затем commit PBIs из backlog.
            </p>
          )}
        </div>
      )}

      {subTab === "burndown" && (
        <div className="rounded-xl border border-border bg-surface p-4">
          {!activeSprintId ? (
            <p className="text-sm text-text-muted">Выберите sprint</p>
          ) : (
            <>
              <p className="mb-3 text-sm text-text-muted">
                Ideal line vs remaining story points (сегодня:{" "}
                {burndown.find((b) => b.remaining != null)?.remaining ?? "—"}{" "}
                SP).
              </p>
              <div className="overflow-x-auto">
                <table className="min-w-full text-left text-xs">
                  <thead className="text-text-muted">
                    <tr>
                      <th className="px-2 py-1">Date</th>
                      <th className="px-2 py-1">Ideal</th>
                      <th className="px-2 py-1">Remaining</th>
                    </tr>
                  </thead>
                  <tbody>
                    {burndown.map((row) => (
                      <tr key={row.date} className="border-t border-border">
                        <td className="px-2 py-1">{row.date}</td>
                        <td className="px-2 py-1">{row.ideal}</td>
                        <td className="px-2 py-1">
                          {row.remaining == null ? "—" : row.remaining}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
