import { useEffect, useMemo, useState } from "react";

import type { CustomField, CustomValue, IssueStatus, Tracker } from "../../api/tracking";
import type { Project, WBSNode } from "../../api/projects";
import { CustomFieldInput } from "./CustomFieldInput";

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
