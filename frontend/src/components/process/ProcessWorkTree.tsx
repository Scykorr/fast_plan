import {
  DndContext,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import type { Attachment } from "../../api/attachments";
import type { ProcessWorkNode } from "../../api/process";
import type { WorkItemComment } from "../../api/projects";
import type { TimeEntry } from "../../api/timelog";
import type { WorkspaceMember } from "../../api/workspace";
import { AssigneeSelect } from "../AssigneeSelect";
import { useAttachmentsApi } from "../../hooks/useAttachmentsApi";
import { useProcessApi } from "../../hooks/useProcessApi";
import { useProjectsApi } from "../../hooks/useProjectsApi";
import { useTimeLogApi } from "../../hooks/useTimeLogApi";
import { CommentThread } from "../comments/CommentThread";
import { GlossaryText, TermHint } from "../TermHint";

type FlatNode = ProcessWorkNode & { depth: number; parent_id: number | null };

type Props = {
  tree: ProcessWorkNode[];
  members?: WorkspaceMember[];
  onSelectBpmn?: (bpmnId: string) => void;
  onPatch?: (
    nodeId: number,
    body: Record<string, unknown>,
  ) => Promise<ProcessWorkNode[]>;
  onReload?: () => Promise<void>;
};

function flatten(
  nodes: ProcessWorkNode[],
  depth = 0,
  parentId: number | null = null,
): FlatNode[] {
  const out: FlatNode[] = [];
  for (const n of nodes) {
    out.push({
      ...n,
      depth,
      parent_id: n.parent_id ?? parentId,
    });
    out.push(...flatten(n.children || [], depth + 1, n.id));
  }
  return out;
}

function findNode(
  nodes: ProcessWorkNode[],
  id: number,
): ProcessWorkNode | null {
  for (const n of nodes) {
    if (n.id === id) return n;
    const child = findNode(n.children || [], id);
    if (child) return child;
  }
  return null;
}

function SortableRow({
  node,
  onSelectBpmn,
  onEdit,
}: {
  node: FlatNode;
  onSelectBpmn?: (bpmnId: string) => void;
  onEdit?: () => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: node.id, data: { parentId: node.parent_id } });

  return (
    <tr
      ref={setNodeRef}
      style={{
        transform: CSS.Transform.toString(transform),
        transition,
        opacity: isDragging ? 0.5 : 1,
      }}
      className="border-t border-border align-top"
    >
      <td className="px-1 py-1.5 text-text-muted">
        <button
          type="button"
          className="cursor-grab px-1 active:cursor-grabbing"
          aria-label="Drag"
          {...attributes}
          {...listeners}
        >
          ⋮⋮
        </button>
      </td>
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
            <span className="ml-1 text-text-muted">· {node.assignee_name}</span>
          )}
          {node.capacity_hint?.overloaded && (
            <span
              className="ml-1 rounded bg-amber-100 px-1 text-[10px] text-amber-800"
              title={node.capacity_hint.hint || "Перегруз"}
            >
              capacity!
            </span>
          )}
        </button>
      </td>
      <td className="px-2 py-1.5 text-text-muted">{node.node_type}</td>
      <td className="px-2 py-1.5">{node.status}</td>
      <td className="px-2 py-1.5">{node.progress}</td>
      <td className="px-2 py-1.5 text-text-muted">
        {node.kanban_column || "—"}
      </td>
      <td className="px-2 py-1.5 text-text-muted">
        {node.time_hours && Number(node.time_hours) > 0 ? node.time_hours : "—"}
      </td>
      <td className="px-2 py-1.5 text-text-muted">
        {node.attachment_count || "—"}
      </td>
      <td className="px-2 py-1.5 text-text-muted">
        {node.start_date || "—"} → {node.end_date || "—"} ({node.duration_days}
        д)
      </td>
      <td className="px-2 py-1.5 text-text-muted">
        R:{node.raci_r || "—"} A:{node.raci_a || "—"} C:{node.raci_c || "—"} I:
        {node.raci_i || "—"}
      </td>
      <td className="px-2 py-1.5">
        {onEdit && (
          <button
            type="button"
            className="text-primary hover:underline"
            onClick={onEdit}
          >
            Edit
          </button>
        )}
      </td>
    </tr>
  );
}

export function ProcessWorkTree({
  tree,
  members = [],
  onSelectBpmn,
  onPatch,
  onReload,
}: Props) {
  const rows = useMemo(() => flatten(tree), [tree]);
  const timeApi = useTimeLogApi();
  const attachmentsApi = useAttachmentsApi();
  const processApi = useProcessApi();
  const projectsApi = useProjectsApi();
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
  );

  const [editingId, setEditingId] = useState<number | null>(null);
  const [assigneeDraft, setAssigneeDraft] = useState<number | null>(null);
  const [raciDraft, setRaciDraft] = useState({ r: "", a: "", c: "", i: "" });
  const [datesDraft, setDatesDraft] = useState({
    start: "",
    end: "",
    duration: "1",
  });
  const [timeHours, setTimeHours] = useState("1");
  const [timeDate, setTimeDate] = useState(
    () => new Date().toISOString().slice(0, 10),
  );
  const [timeNotes, setTimeNotes] = useState("");
  const [entries, setEntries] = useState<TimeEntry[]>([]);
  const [files, setFiles] = useState<Attachment[]>([]);
  const [comments, setComments] = useState<WorkItemComment[]>([]);
  const [panelError, setPanelError] = useState("");

  const editingNode =
    editingId != null ? findNode(tree, editingId) : null;

  useEffect(() => {
    if (editingId == null || !timeApi || !attachmentsApi || !processApi) {
      setEntries([]);
      setFiles([]);
      setComments([]);
      return;
    }
    let cancelled = false;
    void (async () => {
      try {
        const [timeList, fileList, commentList] = await Promise.all([
          timeApi.getEntries({ processWorkNode: editingId }),
          attachmentsApi.getProcessWorkNodeAttachments(editingId),
          processApi.getWorkNodeComments(editingId),
        ]);
        if (!cancelled) {
          setEntries(timeList);
          setFiles(fileList);
          setComments(commentList as WorkItemComment[]);
          setPanelError("");
        }
      } catch {
        if (!cancelled) setPanelError("Не удалось загрузить панель узла");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [editingId, timeApi, attachmentsApi, processApi]);

  const onDragEnd = (event: DragEndEvent) => {
    if (!onPatch) return;
    const activeId = Number(event.active.id);
    const overId = event.over ? Number(event.over.id) : null;
    if (!overId || activeId === overId) return;
    const active = rows.find((r) => r.id === activeId);
    const over = rows.find((r) => r.id === overId);
    if (!active || !over || active.parent_id !== over.parent_id) return;
    const siblings = rows.filter((r) => r.parent_id === active.parent_id);
    const newIndex = siblings.findIndex((r) => r.id === overId);
    if (newIndex < 0) return;
    void onPatch(activeId, { position: newIndex });
  };

  if (rows.length === 0) {
    return (
      <p className="text-sm text-text-muted">
        Дерево ещё не материализовано. Нажмите «Materialize WBS».
      </p>
    );
  }

  const boardId = rows.find((r) => r.board_id != null)?.board_id ?? null;

  return (
    <div className="space-y-3">
      {boardId != null && (
        <p className="text-xs text-text-muted">
          <TermHint term="kanban">Kanban</TermHint> доска процесса:{" "}
          <Link
            to={`/kanban?board=${boardId}`}
            className="text-primary hover:underline"
          >
            открыть #{boardId}
          </Link>
        </p>
      )}
      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragEnd={onDragEnd}
      >
        <div className="overflow-x-auto rounded-lg border border-border">
          <table className="min-w-full text-left text-xs">
            <thead className="bg-cream text-text-muted">
              <tr>
                <th className="px-1 py-1.5" />
                <th className="px-2 py-1.5">Код / узел</th>
                <th className="px-2 py-1.5">Тип</th>
                <th className="px-2 py-1.5">Статус</th>
                <th className="px-2 py-1.5">%</th>
                <th className="px-2 py-1.5">Kanban</th>
                <th className="px-2 py-1.5">Часы</th>
                <th className="px-2 py-1.5">Файлы</th>
                <th className="px-2 py-1.5">Даты</th>
                <th className="px-2 py-1.5">
                  <TermHint term="raci">RACI</TermHint>
                </th>
                <th className="px-2 py-1.5" />
              </tr>
            </thead>
            <SortableContext
              items={rows.map((r) => r.id)}
              strategy={verticalListSortingStrategy}
            >
              <tbody>
                {rows.map((node) => (
                  <SortableRow
                    key={node.id}
                    node={node}
                    onSelectBpmn={onSelectBpmn}
                    onEdit={
                      onPatch
                        ? () => {
                            setEditingId(node.id);
                            setAssigneeDraft(node.assignee_id);
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
                          }
                        : undefined
                    }
                  />
                ))}
              </tbody>
            </SortableContext>
          </table>
        </div>
      </DndContext>

      {editingId != null && onPatch && (
        <div className="space-y-3 rounded-lg border border-border bg-cream p-3 text-xs">
          <p className="font-medium text-text">
            Узел #{editingId}
            {editingNode ? ` · ${editingNode.title}` : ""} · даты /{" "}
            <GlossaryText text="RACI" /> / time / вложения / comments
          </p>
          {panelError && <p className="text-danger">{panelError}</p>}
          <div className="flex flex-wrap gap-2">
            <AssigneeSelect
              members={members}
              value={assigneeDraft}
              onChange={setAssigneeDraft}
              className="rounded border border-border bg-surface px-2 py-1"
              emptyLabel="Исполнитель"
            />
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
                    assignee_id: assigneeDraft,
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

          <div className="space-y-2 border-t border-border pt-2">
            <p className="font-medium text-text">Time log</p>
            <div className="flex flex-wrap items-center gap-2">
              <input
                type="number"
                min={0.25}
                step={0.25}
                value={timeHours}
                onChange={(e) => setTimeHours(e.target.value)}
                className="w-20 rounded border border-border bg-surface px-2 py-1"
              />
              <input
                type="date"
                value={timeDate}
                onChange={(e) => setTimeDate(e.target.value)}
                className="rounded border border-border bg-surface px-2 py-1"
              />
              <input
                type="text"
                placeholder="Заметка"
                value={timeNotes}
                onChange={(e) => setTimeNotes(e.target.value)}
                className="min-w-[10rem] flex-1 rounded border border-border bg-surface px-2 py-1"
              />
              <button
                type="button"
                className="rounded bg-secondary px-3 py-1 text-white"
                disabled={!timeApi}
                onClick={() =>
                  void (async () => {
                    if (!timeApi) return;
                    try {
                      await timeApi.createEntry({
                        process_work_node: editingId,
                        hours: timeHours,
                        work_date: timeDate,
                        notes: timeNotes,
                      });
                      setEntries(
                        await timeApi.getEntries({
                          processWorkNode: editingId,
                        }),
                      );
                      setTimeNotes("");
                      await onReload?.();
                    } catch {
                      setPanelError("Не удалось добавить time entry");
                    }
                  })()
                }
              >
                + часы
              </button>
            </div>
            <ul className="space-y-1 text-text-muted">
              {entries.length === 0 ? (
                <li>Нет записей</li>
              ) : (
                entries.map((e) => (
                  <li key={e.id}>
                    {e.work_date} · {e.hours}h · {e.user_name}
                  </li>
                ))
              )}
            </ul>
          </div>

          <div className="space-y-2 border-t border-border pt-2">
            <p className="font-medium text-text">Вложения</p>
            <input
              type="file"
              disabled={!attachmentsApi}
              onChange={(e) => {
                const file = e.target.files?.[0];
                e.target.value = "";
                if (!file || !attachmentsApi) return;
                void (async () => {
                  try {
                    await attachmentsApi.uploadProcessWorkNodeAttachment(
                      editingId,
                      file,
                    );
                    setFiles(
                      await attachmentsApi.getProcessWorkNodeAttachments(
                        editingId,
                      ),
                    );
                    await onReload?.();
                  } catch {
                    setPanelError("Не удалось загрузить файл");
                  }
                })();
              }}
            />
            <ul className="space-y-1 text-text-muted">
              {files.map((f) => (
                <li key={f.id}>{f.name}</li>
              ))}
            </ul>
          </div>

          <div className="space-y-2 border-t border-border pt-2">
            <p className="font-medium text-text">Comments</p>
            <CommentThread
              comments={comments}
              onAdd={async (body, kind) => {
                if (!processApi) return;
                await processApi.createWorkNodeComment(editingId, {
                  body,
                  kind,
                });
                setComments(
                  (await processApi.getWorkNodeComments(
                    editingId,
                  )) as WorkItemComment[],
                );
              }}
              onDelete={
                projectsApi
                  ? async (id) => {
                      await projectsApi.deleteComment(id);
                      if (!processApi) return;
                      setComments(
                        (await processApi.getWorkNodeComments(
                          editingId,
                        )) as WorkItemComment[],
                      );
                    }
                  : undefined
              }
              canDelete
            />
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
              <div
                key={`g-${n.id}`}
                className="flex items-center gap-2 text-[11px]"
              >
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
