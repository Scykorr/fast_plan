import { useCallback, useEffect, useMemo, useState } from "react";

import { parseApiError } from "../api/errors";
import type { CustomField, IssueStatus, Tracker, TrackingMetadata } from "../api/tracking";
import { ErrorMessage } from "../components/ErrorMessage";
import { useTrackingApi } from "../hooks/useTrackingApi";

import type { CustomFieldFormat } from "../components/tracking/fieldFormats";
import { CUSTOM_FIELD_FORMATS, formatHasEnumerations } from "../components/tracking/fieldFormats";

type Tab = "trackers" | "statuses" | "fields";

export function AdministrationPage() {
  const trackingApi = useTrackingApi();
  const [tab, setTab] = useState<Tab>("trackers");
  const [metadata, setMetadata] = useState<TrackingMetadata | null>(null);
  const [error, setError] = useState("");
  const [newFieldName, setNewFieldName] = useState("");
  const [newFieldFormat, setNewFieldFormat] = useState<CustomFieldFormat>("string");

  const load = useCallback(async () => {
    if (!trackingApi) {
      return;
    }
    try {
      setMetadata(await trackingApi.getMetadata());
    } catch (err) {
      setError(parseApiError(err, "Не удалось загрузить настройки"));
    }
  }, [trackingApi]);

  useEffect(() => {
    void load();
  }, [load]);

  const issueTrackers = useMemo(
    () => metadata?.trackers.filter((item) => item.target === "issue") ?? [],
    [metadata],
  );

  const handleCreateTracker = async () => {
    if (!trackingApi) {
      return;
    }
    const name = window.prompt("Название трекера");
    if (!name?.trim()) {
      return;
    }
    const target = window.prompt("Тип (project/issue)", "issue") as Tracker["target"];
    try {
      await trackingApi.createTracker({
        name: name.trim(),
        target: target === "project" ? "project" : "issue",
      });
      await load();
    } catch (err) {
      setError(parseApiError(err, "Не удалось создать трекер"));
    }
  };

  const handleCreateStatus = async () => {
    if (!trackingApi) {
      return;
    }
    const name = window.prompt("Название статуса");
    if (!name?.trim()) {
      return;
    }
    try {
      await trackingApi.createStatus({ name: name.trim() });
      await load();
    } catch (err) {
      setError(parseApiError(err, "Не удалось создать статус"));
    }
  };

  const handleCreateField = async () => {
    if (!trackingApi || issueTrackers.length === 0) {
      return;
    }
    if (!newFieldName.trim()) {
      setError("Укажите название поля");
      return;
    }
    try {
      await trackingApi.createCustomField({
        name: newFieldName.trim(),
        field_format: newFieldFormat,
        tracker_ids: [issueTrackers[0].id],
        enumerations: [],
      });
      setNewFieldName("");
      setNewFieldFormat("string");
      await load();
    } catch (err) {
      setError(parseApiError(err, "Не удалось создать поле"));
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-text">Администрирование</h1>
        <p className="mt-1 text-sm text-text-muted">
          Трекеры, статусы и кастомные поля workspace (как в Redmine)
        </p>
      </div>

      {error && <ErrorMessage message={error} onDismiss={() => setError("")} />}

      <div className="flex flex-wrap gap-1 border-b border-border">
        {(
          [
            ["trackers", "Трекеры"],
            ["statuses", "Статусы"],
            ["fields", "Кастомные поля"],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            onClick={() => setTab(id)}
            className={[
              "border-b-2 px-3 py-2 text-sm font-medium",
              tab === id
                ? "border-primary text-primary"
                : "border-transparent text-text-muted hover:text-text",
            ].join(" ")}
          >
            {label}
          </button>
        ))}
      </div>

      {!metadata ? (
        <p className="text-text-muted">Загрузка...</p>
      ) : tab === "trackers" ? (
        <TrackerSection
          trackers={metadata.trackers}
          onCreate={handleCreateTracker}
          onUpdate={async (id, body) => {
            await trackingApi?.updateTracker(id, body);
            await load();
          }}
          onDelete={async (id) => {
            if (!window.confirm("Удалить трекер?")) {
              return;
            }
            await trackingApi?.deleteTracker(id);
            await load();
          }}
        />
      ) : tab === "statuses" ? (
        <StatusSection
          statuses={metadata.statuses}
          onCreate={handleCreateStatus}
          onUpdate={async (id, body) => {
            await trackingApi?.updateStatus(id, body);
            await load();
          }}
          onDelete={async (id) => {
            if (!window.confirm("Удалить статус?")) {
              return;
            }
            await trackingApi?.deleteStatus(id);
            await load();
          }}
        />
      ) : (
        <CustomFieldSection
          fields={metadata.custom_fields}
          trackers={metadata.trackers}
          newFieldName={newFieldName}
          newFieldFormat={newFieldFormat}
          onNewFieldNameChange={setNewFieldName}
          onNewFieldFormatChange={setNewFieldFormat}
          onCreate={() => void handleCreateField()}
          onUpdate={async (id, body) => {
            await trackingApi?.updateCustomField(id, body);
            await load();
          }}
          onDelete={async (id) => {
            if (!window.confirm("Удалить кастомное поле?")) {
              return;
            }
            await trackingApi?.deleteCustomField(id);
            await load();
          }}
        />
      )}
    </div>
  );
}

function TrackerSection({
  trackers,
  onCreate,
  onUpdate,
  onDelete,
}: {
  trackers: Tracker[];
  onCreate: () => void;
  onUpdate: (id: number, body: Partial<Tracker>) => Promise<void>;
  onDelete: (id: number) => Promise<void>;
}) {
  return (
    <div className="rounded-xl border border-border bg-surface p-4">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-text">Трекеры</h2>
        <button
          type="button"
          onClick={onCreate}
          className="rounded-lg bg-primary px-3 py-2 text-sm font-semibold text-white"
        >
          + Трекер
        </button>
      </div>
      <div className="space-y-2">
        {trackers.map((tracker) => (
          <div
            key={tracker.id}
            className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-border px-3 py-2"
          >
            <div>
              <p className="font-medium text-text">{tracker.name}</p>
              <p className="text-xs text-text-muted">
                {tracker.target === "project" ? "Проект" : "Задача"}
                {tracker.is_default ? " · по умолчанию" : ""}
              </p>
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                className="text-sm text-primary hover:underline"
                onClick={() => {
                  const name = window.prompt("Название", tracker.name);
                  if (name?.trim()) {
                    void onUpdate(tracker.id, { name: name.trim() });
                  }
                }}
              >
                Изменить
              </button>
              <button
                type="button"
                className="text-sm text-primary hover:underline"
                onClick={() => void onDelete(tracker.id)}
              >
                Удалить
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function StatusSection({
  statuses,
  onCreate,
  onUpdate,
  onDelete,
}: {
  statuses: IssueStatus[];
  onCreate: () => void;
  onUpdate: (id: number, body: Partial<IssueStatus>) => Promise<void>;
  onDelete: (id: number) => Promise<void>;
}) {
  return (
    <div className="rounded-xl border border-border bg-surface p-4">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-text">Статусы</h2>
        <button
          type="button"
          onClick={onCreate}
          className="rounded-lg bg-primary px-3 py-2 text-sm font-semibold text-white"
        >
          + Статус
        </button>
      </div>
      <div className="space-y-2">
        {statuses.map((status) => (
          <div
            key={status.id}
            className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-border px-3 py-2"
          >
            <div>
              <p className="font-medium text-text">{status.name}</p>
              <p className="text-xs text-text-muted">
                {status.is_closed ? "Закрывающий" : "Открытый"}
                {status.is_default ? " · по умолчанию" : ""}
              </p>
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                className="text-sm text-primary hover:underline"
                onClick={() => {
                  const name = window.prompt("Название", status.name);
                  if (name?.trim()) {
                    void onUpdate(status.id, { name: name.trim() });
                  }
                }}
              >
                Изменить
              </button>
              <button
                type="button"
                className="text-sm text-primary hover:underline"
                onClick={() => void onDelete(status.id)}
              >
                Удалить
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function CustomFieldSection({
  fields,
  trackers,
  newFieldName,
  newFieldFormat,
  onNewFieldNameChange,
  onNewFieldFormatChange,
  onCreate,
  onUpdate,
  onDelete,
}: {
  fields: CustomField[];
  trackers: Tracker[];
  newFieldName: string;
  newFieldFormat: CustomFieldFormat;
  onNewFieldNameChange: (value: string) => void;
  onNewFieldFormatChange: (value: CustomFieldFormat) => void;
  onCreate: () => void;
  onUpdate: (id: number, body: Partial<CustomField>) => Promise<void>;
  onDelete: (id: number) => Promise<void>;
}) {
  return (
    <div className="rounded-xl border border-border bg-surface p-4">
      <h2 className="mb-4 text-lg font-semibold text-text">Кастомные поля</h2>

      <div className="mb-6 flex flex-wrap items-end gap-3 rounded-lg border border-dashed border-border p-3">
        <label className="min-w-48 flex-1 text-sm">
          <span className="text-text-muted">Название</span>
          <input
            value={newFieldName}
            onChange={(event) => onNewFieldNameChange(event.target.value)}
            className="mt-1 w-full rounded-lg border border-border px-3 py-2"
            placeholder="Например, Приоритет"
          />
        </label>
        <label className="min-w-56 text-sm">
          <span className="text-text-muted">Тип данных</span>
          <select
            value={newFieldFormat}
            onChange={(event) =>
              onNewFieldFormatChange(event.target.value as CustomFieldFormat)
            }
            className="mt-1 w-full rounded-lg border border-border px-3 py-2"
          >
            {CUSTOM_FIELD_FORMATS.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          onClick={onCreate}
          className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white"
        >
          + Поле
        </button>
      </div>
      <p className="mb-4 text-xs text-text-muted">
        {CUSTOM_FIELD_FORMATS.find((item) => item.value === newFieldFormat)?.description}
      </p>

      <div className="space-y-4">
        {fields.map((field) => (
          <div key={field.id} className="rounded-lg border border-border p-3">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <p className="font-medium text-text">{field.name}</p>
                <label className="mt-1 block text-xs text-text-muted">
                  Тип данных
                  <select
                    value={field.field_format}
                    onChange={(event) =>
                      void onUpdate(field.id, {
                        field_format: event.target.value,
                        enumerations: formatHasEnumerations(event.target.value)
                          ? field.enumerations
                          : [],
                      })
                    }
                    className="ml-2 rounded border border-border px-2 py-0.5 text-xs text-text"
                  >
                    {CUSTOM_FIELD_FORMATS.map((item) => (
                      <option key={item.value} value={item.value}>
                        {item.label}
                      </option>
                    ))}
                  </select>
                </label>
                <p className="mt-1 text-xs text-text-muted">
                  {CUSTOM_FIELD_FORMATS.find((item) => item.value === field.field_format)
                    ?.description ?? field.field_format}
                  {field.is_required ? " · обязательное" : ""}
                </p>
                <p className="mt-1 text-xs text-text-muted">
                  Трекеры:{" "}
                  {field.tracker_ids
                    .map((id) => trackers.find((tracker) => tracker.id === id)?.name ?? id)
                    .join(", ")}
                </p>
              </div>
              <div className="flex gap-2">
                <button
                  type="button"
                  className="text-sm text-primary hover:underline"
                  onClick={() => {
                    const name = window.prompt("Название", field.name);
                    if (name?.trim()) {
                      void onUpdate(field.id, { name: name.trim() });
                    }
                  }}
                >
                  Переименовать
                </button>
                <button
                  type="button"
                  className="text-sm text-primary hover:underline"
                  onClick={() => void onDelete(field.id)}
                >
                  Удалить
                </button>
              </div>
            </div>

            {field.field_format === "list" && (
              <EnumerationEditor
                field={field}
                onUpdate={onUpdate}
                mode="flat"
              />
            )}

            {field.field_format === "link_list" && (
              <EnumerationEditor
                field={field}
                onUpdate={onUpdate}
                mode="linked"
              />
            )}

            <div className="mt-3">
              <p className="mb-1 text-xs font-medium text-text-muted">Привязка к трекерам</p>
              <div className="flex flex-wrap gap-2">
                {trackers.map((tracker) => {
                  const checked = field.tracker_ids.includes(tracker.id);
                  return (
                    <label key={tracker.id} className="flex items-center gap-1 text-xs">
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => {
                          const trackerIds = checked
                            ? field.tracker_ids.filter((id) => id !== tracker.id)
                            : [...field.tracker_ids, tracker.id];
                          void onUpdate(field.id, { tracker_ids: trackerIds });
                        }}
                      />
                      {tracker.name}
                    </label>
                  );
                })}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function EnumerationEditor({
  field,
  onUpdate,
  mode,
}: {
  field: CustomField;
  onUpdate: (id: number, body: Partial<CustomField>) => Promise<void>;
  mode: "flat" | "linked";
}) {
  if (mode === "flat") {
    return (
      <div className="mt-3">
        <p className="mb-1 text-xs font-medium text-text-muted">Значения списка</p>
        <div className="flex flex-wrap gap-2">
          {field.enumerations
            .filter((item) => !item.parent_id)
            .map((item) => (
              <span
                key={item.id}
                className="rounded-full bg-cream px-2 py-1 text-xs text-text"
              >
                {item.name}
              </span>
            ))}
          <button
            type="button"
            className="text-xs text-primary hover:underline"
            onClick={() => {
              const value = window.prompt("Новое значение списка");
              if (!value?.trim()) {
                return;
              }
              void onUpdate(field.id, {
                enumerations: [
                  ...field.enumerations,
                  {
                    id: 0,
                    name: value.trim(),
                    position: field.enumerations.length,
                    is_active: true,
                    parent_id: null,
                  },
                ],
              });
            }}
          >
            + значение
          </button>
        </div>
      </div>
    );
  }

  const parents = field.enumerations.filter((item) => !item.parent_id);

  return (
    <div className="mt-3 space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium text-text-muted">Связанные списки</p>
        <button
          type="button"
          className="text-xs text-primary hover:underline"
          onClick={() => {
            const value = window.prompt("Название родительской категории");
            if (!value?.trim()) {
              return;
            }
            void onUpdate(field.id, {
              enumerations: [
                ...field.enumerations,
                {
                  id: 0,
                  name: value.trim(),
                  position: parents.length,
                  is_active: true,
                  parent_id: null,
                },
              ],
            });
          }}
        >
          + категория
        </button>
      </div>
      {parents.map((parent) => (
        <div key={parent.id} className="rounded-lg bg-cream/60 p-2">
          <p className="text-xs font-semibold text-text">{parent.name}</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {field.enumerations
              .filter((item) => item.parent_id === parent.id)
              .map((child) => (
                <span
                  key={child.id}
                  className="rounded-full bg-surface px-2 py-1 text-xs text-text"
                >
                  {child.name}
                </span>
              ))}
            <button
              type="button"
              className="text-xs text-primary hover:underline"
              onClick={() => {
                const value = window.prompt(`Значение для «${parent.name}»`);
                if (!value?.trim()) {
                  return;
                }
                void onUpdate(field.id, {
                  enumerations: [
                    ...field.enumerations,
                    {
                      id: 0,
                      name: value.trim(),
                      position: field.enumerations.filter(
                        (item) => item.parent_id === parent.id,
                      ).length,
                      is_active: true,
                      parent_id: parent.id,
                    },
                  ],
                });
              }}
            >
              + значение
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
