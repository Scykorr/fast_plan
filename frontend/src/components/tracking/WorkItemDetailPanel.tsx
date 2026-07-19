import { useEffect, useMemo, useState } from "react";

import type { Attachment } from "../../api/attachments";
import { parseApiError } from "../../api/errors";
import type { CustomField, CustomValue, IssueStatus, Tracker } from "../../api/tracking";
import type { Project, WBSNode } from "../../api/projects";
import type { TimeEntry } from "../../api/timelog";
import { useAttachmentsApi } from "../../hooks/useAttachmentsApi";
import { useTimeLogApi } from "../../hooks/useTimeLogApi";
import { CustomFieldInput } from "./CustomFieldInput";

function formatBytes(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} Б`;
  }
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} КБ`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} МБ`;
}

function WbsAttachments({ wbsId }: { wbsId: number }) {
  const attachmentsApi = useAttachmentsApi();
  const [items, setItems] = useState<Attachment[]>([]);
  const [error, setError] = useState("");
  const [uploading, setUploading] = useState(false);

  const load = async () => {
    if (!attachmentsApi) {
      return;
    }
    try {
      setItems(await attachmentsApi.getWbsAttachments(wbsId));
    } catch (err) {
      setError(parseApiError(err, "Не удалось загрузить вложения"));
    }
  };

  useEffect(() => {
    setItems([]);
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [wbsId, attachmentsApi]);

  const handleUpload = async (files: FileList | null) => {
    const file = files?.[0];
    if (!file || !attachmentsApi) {
      return;
    }
    setUploading(true);
    setError("");
    try {
      await attachmentsApi.uploadWbsAttachment(wbsId, file);
      await load();
    } catch (err) {
      setError(parseApiError(err, "Не удалось загрузить файл"));
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!attachmentsApi) {
      return;
    }
    try {
      await attachmentsApi.deleteAttachment(id);
      await load();
    } catch (err) {
      setError(parseApiError(err, "Не удалось удалить вложение"));
    }
  };

  return (
    <div className="border-t border-border pt-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-text">Вложения</h3>
        <label className="cursor-pointer rounded-lg border border-border bg-cream px-3 py-1.5 text-xs font-medium text-text hover:bg-border/30">
          {uploading ? "Загрузка..." : "+ Файл"}
          <input
            type="file"
            className="hidden"
            disabled={uploading}
            onChange={(event) => void handleUpload(event.target.files)}
          />
        </label>
      </div>
      {error && <p className="mb-2 text-xs text-primary">{error}</p>}
      {items.length === 0 ? (
        <p className="text-xs text-text-muted">Файлов пока нет</p>
      ) : (
        <ul className="space-y-2">
          {items.map((item) => (
            <li
              key={item.id}
              className="flex items-center justify-between gap-2 rounded-lg border border-border bg-cream/50 px-3 py-2 text-xs"
            >
              <a
                href={item.url ?? "#"}
                target="_blank"
                rel="noreferrer"
                className="truncate font-medium text-primary hover:underline"
              >
                {item.name}
              </a>
              <span className="whitespace-nowrap text-text-muted">
                {formatBytes(item.size)} · {item.uploaded_by_name ?? "—"}
              </span>
              <button
                type="button"
                onClick={() => void handleDelete(item.id)}
                className="text-text-muted hover:text-primary"
                aria-label={`Удалить ${item.name}`}
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function WbsTimeLog({ wbsId }: { wbsId: number }) {
  const timeLogApi = useTimeLogApi();
  const [entries, setEntries] = useState<TimeEntry[]>([]);
  const [hours, setHours] = useState("");
  const [workDate, setWorkDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [notes, setNotes] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const load = async () => {
    if (!timeLogApi) {
      return;
    }
    try {
      setEntries(await timeLogApi.getEntries({ wbsNode: wbsId }));
    } catch (err) {
      setError(parseApiError(err, "Не удалось загрузить учёт времени"));
    }
  };

  useEffect(() => {
    setEntries([]);
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [wbsId, timeLogApi]);

  const totalHours = useMemo(
    () => entries.reduce((sum, entry) => sum + Number(entry.hours), 0),
    [entries],
  );

  const handleAdd = async () => {
    if (!timeLogApi) {
      return;
    }
    const parsedHours = Number(hours);
    if (!Number.isFinite(parsedHours) || parsedHours <= 0) {
      setError("Укажите число часов больше нуля");
      return;
    }
    setSaving(true);
    setError("");
    try {
      await timeLogApi.createEntry({
        wbs_node: wbsId,
        hours: String(parsedHours),
        work_date: workDate,
        notes,
      });
      setHours("");
      setNotes("");
      await load();
    } catch (err) {
      setError(parseApiError(err, "Не удалось сохранить время"));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!timeLogApi) {
      return;
    }
    try {
      await timeLogApi.deleteEntry(id);
      await load();
    } catch (err) {
      setError(parseApiError(err, "Не удалось удалить запись"));
    }
  };

  return (
    <div className="border-t border-border pt-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-text">Учёт времени</h3>
        <span className="text-xs text-text-muted">Итого: {totalHours}ч</span>
      </div>
      {error && <p className="mb-2 text-xs text-primary">{error}</p>}
      <div className="mb-3 flex flex-wrap items-end gap-2">
        <label className="text-xs">
          <span className="mb-1 block text-text-muted">Дата</span>
          <input
            type="date"
            value={workDate}
            onChange={(event) => setWorkDate(event.target.value)}
            className="rounded-lg border border-border px-2 py-1.5 text-xs"
          />
        </label>
        <label className="text-xs">
          <span className="mb-1 block text-text-muted">Часы</span>
          <input
            type="number"
            min="0"
            step="0.25"
            value={hours}
            onChange={(event) => setHours(event.target.value)}
            className="w-20 rounded-lg border border-border px-2 py-1.5 text-xs"
          />
        </label>
        <label className="min-w-32 flex-1 text-xs">
          <span className="mb-1 block text-text-muted">Заметка</span>
          <input
            type="text"
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
            className="w-full rounded-lg border border-border px-2 py-1.5 text-xs"
          />
        </label>
        <button
          type="button"
          disabled={saving}
          onClick={() => void handleAdd()}
          className="rounded-lg bg-primary px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-60"
        >
          {saving ? "..." : "Добавить"}
        </button>
      </div>
      {entries.length === 0 ? (
        <p className="text-xs text-text-muted">Записей пока нет</p>
      ) : (
        <ul className="space-y-2">
          {entries.map((entry) => (
            <li
              key={entry.id}
              className="flex items-center justify-between gap-2 rounded-lg border border-border bg-cream/50 px-3 py-2 text-xs"
            >
              <span>
                {entry.work_date} · {entry.hours}ч · {entry.user_name}
                {entry.notes ? ` — ${entry.notes}` : ""}
              </span>
              <button
                type="button"
                onClick={() => void handleDelete(entry.id)}
                className="text-text-muted hover:text-primary"
                aria-label="Удалить запись"
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

type WorkItemDetailPanelProps = {
  mode: "project" | "issue";
  project: Project;
  node: WBSNode | null;
  metadata: {
    trackers: Tracker[];
    statuses: IssueStatus[];
    custom_fields: CustomField[];
  };
  onClose: () => void;
  onSaveProject: (body: {
    name?: string;
    description?: string;
    tracker_id?: number | null;
    workflow_status_id?: number | null;
    custom_values?: Record<string, string>;
  }) => void;
  onSaveNode: (
    nodeId: number,
    body: {
      title?: string;
      description?: string;
      tracker_id?: number | null;
      workflow_status_id?: number | null;
      assignee_id?: number | null;
      custom_values?: Record<string, string>;
    },
  ) => void;
};

function valuesMap(values: CustomValue[]): Record<string, string> {
  return Object.fromEntries(values.map((item) => [String(item.field_id), item.value]));
}

function applicableFields(
  fields: CustomField[],
  trackerId: number | null,
): CustomField[] {
  if (!trackerId) {
    return [];
  }
  return fields.filter((field) => field.tracker_ids.includes(trackerId));
}

export function WorkItemDetailPanel({
  mode,
  project,
  node,
  metadata,
  onClose,
  onSaveProject,
  onSaveNode,
}: WorkItemDetailPanelProps) {
  const isProject = mode === "project";
  const trackers = useMemo(
    () =>
      metadata.trackers.filter((item) =>
        isProject ? item.target === "project" : item.target === "issue",
      ),
    [metadata.trackers, isProject],
  );

  const [title, setTitle] = useState(isProject ? project.name : node?.title ?? "");
  const [description, setDescription] = useState(
    isProject ? project.description : node?.description ?? "",
  );
  const [trackerId, setTrackerId] = useState<number | "">(
    isProject ? project.tracker_id ?? "" : node?.tracker_id ?? "",
  );
  const [statusId, setStatusId] = useState<number | "">(
    isProject ? project.workflow_status_id ?? "" : node?.workflow_status_id ?? "",
  );
  const [assigneeId, setAssigneeId] = useState<number | "">(
    isProject ? "" : node?.assignee_id ?? "",
  );
  const [customValues, setCustomValues] = useState<Record<string, string>>(
    valuesMap(isProject ? project.custom_values : node?.custom_values ?? []),
  );

  useEffect(() => {
    setTitle(isProject ? project.name : node?.title ?? "");
    setDescription(isProject ? project.description : node?.description ?? "");
    setTrackerId(isProject ? project.tracker_id ?? "" : node?.tracker_id ?? "");
    setStatusId(
      isProject ? project.workflow_status_id ?? "" : node?.workflow_status_id ?? "",
    );
    setAssigneeId(isProject ? "" : node?.assignee_id ?? "");
    setCustomValues(
      valuesMap(isProject ? project.custom_values : node?.custom_values ?? []),
    );
  }, [isProject, project, node]);

  const fields = applicableFields(
    metadata.custom_fields,
    trackerId === "" ? null : Number(trackerId),
  );

  const handleSave = () => {
    if (isProject) {
      onSaveProject({
        name: title,
        description,
        tracker_id: trackerId === "" ? null : Number(trackerId),
        workflow_status_id: statusId === "" ? null : Number(statusId),
        custom_values: customValues,
      });
      return;
    }
    if (!node) {
      return;
    }
    onSaveNode(node.id, {
      title,
      description,
      tracker_id: trackerId === "" ? null : Number(trackerId),
      workflow_status_id: statusId === "" ? null : Number(statusId),
      assignee_id: assigneeId === "" ? null : Number(assigneeId),
      custom_values: customValues,
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/30">
      <button type="button" className="flex-1" aria-label="Закрыть" onClick={onClose} />
      <div className="flex h-full w-full max-w-xl flex-col overflow-y-auto border-l border-border bg-surface shadow-xl">
        <div className="flex items-center justify-between border-b border-border px-5 py-4">
          <div>
            <p className="text-xs uppercase tracking-wide text-text-muted">
              {isProject ? "Проект" : "Задача WBS"}
            </p>
            <h2 className="text-xl font-bold text-text">
              {isProject ? project.name : `${node?.code} ${node?.title}`}
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg px-3 py-2 text-sm text-text-muted hover:bg-cream"
          >
            Закрыть
          </button>
        </div>

        <div className="space-y-4 p-5">
          <label className="block text-sm">
            <span className="text-text-muted">{isProject ? "Название проекта" : "Тема"}</span>
            <input
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              className="mt-1 w-full rounded-lg border border-border px-3 py-2"
            />
          </label>

          <label className="block text-sm">
            <span className="text-text-muted">Описание</span>
            <textarea
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              rows={4}
              className="mt-1 w-full rounded-lg border border-border px-3 py-2"
            />
          </label>

          <label className="block text-sm">
            <span className="text-text-muted">Трекер</span>
            <select
              value={trackerId}
              onChange={(event) =>
                setTrackerId(event.target.value ? Number(event.target.value) : "")
              }
              className="mt-1 w-full rounded-lg border border-border px-3 py-2"
            >
              <option value="">—</option>
              {trackers.map((tracker) => (
                <option key={tracker.id} value={tracker.id}>
                  {tracker.name}
                </option>
              ))}
            </select>
          </label>

          <label className="block text-sm">
            <span className="text-text-muted">Статус</span>
            <select
              value={statusId}
              onChange={(event) =>
                setStatusId(event.target.value ? Number(event.target.value) : "")
              }
              className="mt-1 w-full rounded-lg border border-border px-3 py-2"
            >
              <option value="">—</option>
              {metadata.statuses.map((status) => (
                <option key={status.id} value={status.id}>
                  {status.name}
                </option>
              ))}
            </select>
          </label>

          {!isProject && (
            <>
              <label className="block text-sm">
                <span className="text-text-muted">Тип узла</span>
                <input
                  value={node?.node_type ?? ""}
                  disabled
                  className="mt-1 w-full rounded-lg border border-border bg-cream px-3 py-2"
                />
              </label>
              <label className="block text-sm">
                <span className="text-text-muted">ID исполнителя</span>
                <input
                  type="number"
                  value={assigneeId}
                  onChange={(event) =>
                    setAssigneeId(event.target.value ? Number(event.target.value) : "")
                  }
                  className="mt-1 w-full rounded-lg border border-border px-3 py-2"
                />
              </label>
              {node?.schedule && (
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <p className="text-text-muted">Начало</p>
                    <p>{node.schedule.start_date}</p>
                  </div>
                  <div>
                    <p className="text-text-muted">Окончание</p>
                    <p>{node.schedule.end_date}</p>
                  </div>
                  <div>
                    <p className="text-text-muted">Прогресс</p>
                    <p>{node.schedule.progress}%</p>
                  </div>
                </div>
              )}
            </>
          )}

          {isProject && (
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <p className="text-text-muted">PMBOK статус</p>
                <p>{project.status}</p>
              </div>
              <div>
                <p className="text-text-muted">Бюджет</p>
                <p>{project.budget}</p>
              </div>
            </div>
          )}

          {fields.length > 0 && (
            <div className="border-t border-border pt-4">
              <h3 className="mb-3 text-sm font-semibold text-text">Кастомные поля</h3>
              <div className="space-y-3">
                {fields.map((field) => (
                  <CustomFieldInput
                    key={field.id}
                    field={field}
                    value={customValues[String(field.id)] ?? ""}
                    onChange={(value) =>
                      setCustomValues((current) => ({
                        ...current,
                        [String(field.id)]: value,
                      }))
                    }
                  />
                ))}
              </div>
            </div>
          )}

          {!isProject && node && (
            <>
              <WbsAttachments wbsId={node.id} />
              <WbsTimeLog wbsId={node.id} />
            </>
          )}
        </div>

        <div className="mt-auto border-t border-border p-5">
          <button
            type="button"
            onClick={handleSave}
            className="w-full rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white"
          >
            Сохранить
          </button>
        </div>
      </div>
    </div>
  );
}
