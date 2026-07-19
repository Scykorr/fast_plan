import { useCallback, useEffect, useMemo, useState } from "react";

import { parseApiError } from "../api/errors";
import type { CustomField, IssueStatus, Tracker, TrackingMetadata } from "../api/tracking";
import { ErrorMessage } from "../components/ErrorMessage";
import { useTrackingApi } from "../hooks/useTrackingApi";

import type { CustomFieldFormat } from "../components/tracking/fieldFormats";
import { CUSTOM_FIELD_FORMATS, formatHasEnumerations } from "../components/tracking/fieldFormats";

type Tab = "trackers" | "statuses" | "fields";

const inputClass = "mt-1 w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text";
const labelClass = "block text-sm text-text-muted";
const primaryBtnClass = "rounded-lg bg-primary px-3 py-2 text-sm font-semibold text-white";
const linkBtnClass = "text-sm text-primary hover:underline";
const checkboxLabelClass = "flex items-center gap-2 text-sm text-text";

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

  const handleCreateTracker = async (body: {
    name: string;
    target: Tracker["target"];
    description?: string;
    is_default?: boolean;
  }) => {
    if (!trackingApi) {
      return;
    }
    try {
      await trackingApi.createTracker(body);
      await load();
    } catch (err) {
      setError(parseApiError(err, "Не удалось создать трекер"));
    }
  };

  const handleCreateStatus = async (body: {
    name: string;
    is_closed?: boolean;
    is_default?: boolean;
  }) => {
    if (!trackingApi) {
      return;
    }
    try {
      await trackingApi.createStatus(body);
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
            try {
              await trackingApi?.updateTracker(id, body);
              await load();
            } catch (err) {
              setError(parseApiError(err, "Не удалось обновить трекер"));
            }
          }}
          onDelete={async (id) => {
            if (!window.confirm("Удалить трекер?")) {
              return;
            }
            try {
              await trackingApi?.deleteTracker(id);
              await load();
            } catch (err) {
              setError(parseApiError(err, "Не удалось удалить трекер"));
            }
          }}
        />
      ) : tab === "statuses" ? (
        <StatusSection
          statuses={metadata.statuses}
          onCreate={handleCreateStatus}
          onUpdate={async (id, body) => {
            try {
              await trackingApi?.updateStatus(id, body);
              await load();
            } catch (err) {
              setError(parseApiError(err, "Не удалось обновить статус"));
            }
          }}
          onDelete={async (id) => {
            if (!window.confirm("Удалить статус?")) {
              return;
            }
            try {
              await trackingApi?.deleteStatus(id);
              await load();
            } catch (err) {
              setError(parseApiError(err, "Не удалось удалить статус"));
            }
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
            try {
              await trackingApi?.updateCustomField(id, body);
              await load();
            } catch (err) {
              setError(parseApiError(err, "Не удалось обновить поле"));
            }
          }}
          onDelete={async (id) => {
            if (!window.confirm("Удалить кастомное поле?")) {
              return;
            }
            try {
              await trackingApi?.deleteCustomField(id);
              await load();
            } catch (err) {
              setError(parseApiError(err, "Не удалось удалить поле"));
            }
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
  onCreate: (body: {
    name: string;
    target: Tracker["target"];
    description?: string;
    is_default?: boolean;
  }) => Promise<void>;
  onUpdate: (id: number, body: Partial<Tracker>) => Promise<void>;
  onDelete: (id: number) => Promise<void>;
}) {
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [target, setTarget] = useState<Tracker["target"]>("issue");
  const [description, setDescription] = useState("");
  const [isDefault, setIsDefault] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editName, setEditName] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [editIsDefault, setEditIsDefault] = useState(false);

  const resetCreateForm = () => {
    setName("");
    setTarget("issue");
    setDescription("");
    setIsDefault(false);
    setShowForm(false);
  };

  const startEdit = (tracker: Tracker) => {
    setEditingId(tracker.id);
    setEditName(tracker.name);
    setEditDescription(tracker.description ?? "");
    setEditIsDefault(tracker.is_default);
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditName("");
    setEditDescription("");
    setEditIsDefault(false);
  };

  return (
    <div className="rounded-xl border border-border bg-surface p-4">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-text">Трекеры</h2>
        {!showForm && (
          <button type="button" onClick={() => setShowForm(true)} className={primaryBtnClass}>
            + Трекер
          </button>
        )}
      </div>

      {showForm && (
        <form
          className="mb-4 space-y-3 rounded-lg border border-dashed border-border p-3"
          onSubmit={(event) => {
            event.preventDefault();
            if (!name.trim()) {
              return;
            }
            void onCreate({
              name: name.trim(),
              target,
              description: description.trim(),
              is_default: isDefault,
            }).then(resetCreateForm);
          }}
        >
          <div className="flex flex-wrap items-end gap-3">
            <label className={`min-w-48 flex-1 ${labelClass}`}>
              Название
              <input
                value={name}
                onChange={(event) => setName(event.target.value)}
                className={inputClass}
                placeholder="Например, Bug"
                required
              />
            </label>
            <label className={`min-w-40 ${labelClass}`}>
              Тип
              <select
                value={target}
                onChange={(event) => setTarget(event.target.value as Tracker["target"])}
                className={inputClass}
              >
                <option value="issue">Задача</option>
                <option value="project">Проект</option>
              </select>
            </label>
          </div>
          <label className={labelClass}>
            Описание (необязательно)
            <input
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              className={inputClass}
              placeholder="Краткое описание"
            />
          </label>
          <label className={checkboxLabelClass}>
            <input
              type="checkbox"
              checked={isDefault}
              onChange={(event) => setIsDefault(event.target.checked)}
            />
            По умолчанию
          </label>
          <div className="flex gap-2">
            <button type="submit" className={primaryBtnClass}>
              Создать
            </button>
            <button
              type="button"
              onClick={resetCreateForm}
              className="rounded-lg border border-border px-3 py-2 text-sm text-text-muted hover:text-text"
            >
              Отмена
            </button>
          </div>
        </form>
      )}

      <div className="space-y-2">
        {trackers.map((tracker) => (
          <div
            key={tracker.id}
            className="rounded-lg border border-border px-3 py-2"
          >
            {editingId === tracker.id ? (
              <form
                className="space-y-3"
                onSubmit={(event) => {
                  event.preventDefault();
                  if (!editName.trim()) {
                    return;
                  }
                  void onUpdate(tracker.id, {
                    name: editName.trim(),
                    description: editDescription.trim(),
                    is_default: editIsDefault,
                  }).then(cancelEdit);
                }}
              >
                <label className={labelClass}>
                  Название
                  <input
                    value={editName}
                    onChange={(event) => setEditName(event.target.value)}
                    className={inputClass}
                    required
                  />
                </label>
                <label className={labelClass}>
                  Описание
                  <input
                    value={editDescription}
                    onChange={(event) => setEditDescription(event.target.value)}
                    className={inputClass}
                  />
                </label>
                <label className={checkboxLabelClass}>
                  <input
                    type="checkbox"
                    checked={editIsDefault}
                    onChange={(event) => setEditIsDefault(event.target.checked)}
                  />
                  По умолчанию
                </label>
                <div className="flex gap-2">
                  <button type="submit" className={primaryBtnClass}>
                    Сохранить
                  </button>
                  <button
                    type="button"
                    onClick={cancelEdit}
                    className="rounded-lg border border-border px-3 py-2 text-sm text-text-muted hover:text-text"
                  >
                    Отмена
                  </button>
                </div>
              </form>
            ) : (
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <p className="font-medium text-text">{tracker.name}</p>
                  <p className="text-xs text-text-muted">
                    {tracker.target === "project" ? "Проект" : "Задача"}
                    {tracker.is_default ? " · по умолчанию" : ""}
                  </p>
                  {tracker.description ? (
                    <p className="mt-1 text-xs text-text-muted">{tracker.description}</p>
                  ) : null}
                </div>
                <div className="flex gap-2">
                  <button
                    type="button"
                    className={linkBtnClass}
                    onClick={() => startEdit(tracker)}
                  >
                    Изменить
                  </button>
                  <button
                    type="button"
                    className={linkBtnClass}
                    onClick={() => void onDelete(tracker.id)}
                  >
                    Удалить
                  </button>
                </div>
              </div>
            )}
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
  onCreate: (body: {
    name: string;
    is_closed?: boolean;
    is_default?: boolean;
  }) => Promise<void>;
  onUpdate: (id: number, body: Partial<IssueStatus>) => Promise<void>;
  onDelete: (id: number) => Promise<void>;
}) {
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [isClosed, setIsClosed] = useState(false);
  const [isDefault, setIsDefault] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editName, setEditName] = useState("");
  const [editIsClosed, setEditIsClosed] = useState(false);
  const [editIsDefault, setEditIsDefault] = useState(false);

  const resetCreateForm = () => {
    setName("");
    setIsClosed(false);
    setIsDefault(false);
    setShowForm(false);
  };

  const startEdit = (status: IssueStatus) => {
    setEditingId(status.id);
    setEditName(status.name);
    setEditIsClosed(status.is_closed);
    setEditIsDefault(status.is_default);
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditName("");
    setEditIsClosed(false);
    setEditIsDefault(false);
  };

  return (
    <div className="rounded-xl border border-border bg-surface p-4">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-text">Статусы</h2>
        {!showForm && (
          <button type="button" onClick={() => setShowForm(true)} className={primaryBtnClass}>
            + Статус
          </button>
        )}
      </div>

      {showForm && (
        <form
          className="mb-4 space-y-3 rounded-lg border border-dashed border-border p-3"
          onSubmit={(event) => {
            event.preventDefault();
            if (!name.trim()) {
              return;
            }
            void onCreate({
              name: name.trim(),
              is_closed: isClosed,
              is_default: isDefault,
            }).then(resetCreateForm);
          }}
        >
          <label className={`min-w-48 ${labelClass}`}>
            Название
            <input
              value={name}
              onChange={(event) => setName(event.target.value)}
              className={inputClass}
              placeholder="Например, В работе"
              required
            />
          </label>
          <div className="flex flex-wrap gap-4">
            <label className={checkboxLabelClass}>
              <input
                type="checkbox"
                checked={isClosed}
                onChange={(event) => setIsClosed(event.target.checked)}
              />
              Закрывающий
            </label>
            <label className={checkboxLabelClass}>
              <input
                type="checkbox"
                checked={isDefault}
                onChange={(event) => setIsDefault(event.target.checked)}
              />
              По умолчанию
            </label>
          </div>
          <div className="flex gap-2">
            <button type="submit" className={primaryBtnClass}>
              Создать
            </button>
            <button
              type="button"
              onClick={resetCreateForm}
              className="rounded-lg border border-border px-3 py-2 text-sm text-text-muted hover:text-text"
            >
              Отмена
            </button>
          </div>
        </form>
      )}

      <div className="space-y-2">
        {statuses.map((status) => (
          <div key={status.id} className="rounded-lg border border-border px-3 py-2">
            {editingId === status.id ? (
              <form
                className="space-y-3"
                onSubmit={(event) => {
                  event.preventDefault();
                  if (!editName.trim()) {
                    return;
                  }
                  void onUpdate(status.id, {
                    name: editName.trim(),
                    is_closed: editIsClosed,
                    is_default: editIsDefault,
                  }).then(cancelEdit);
                }}
              >
                <label className={labelClass}>
                  Название
                  <input
                    value={editName}
                    onChange={(event) => setEditName(event.target.value)}
                    className={inputClass}
                    required
                  />
                </label>
                <div className="flex flex-wrap gap-4">
                  <label className={checkboxLabelClass}>
                    <input
                      type="checkbox"
                      checked={editIsClosed}
                      onChange={(event) => setEditIsClosed(event.target.checked)}
                    />
                    Закрывающий
                  </label>
                  <label className={checkboxLabelClass}>
                    <input
                      type="checkbox"
                      checked={editIsDefault}
                      onChange={(event) => setEditIsDefault(event.target.checked)}
                    />
                    По умолчанию
                  </label>
                </div>
                <div className="flex gap-2">
                  <button type="submit" className={primaryBtnClass}>
                    Сохранить
                  </button>
                  <button
                    type="button"
                    onClick={cancelEdit}
                    className="rounded-lg border border-border px-3 py-2 text-sm text-text-muted hover:text-text"
                  >
                    Отмена
                  </button>
                </div>
              </form>
            ) : (
              <div className="flex flex-wrap items-center justify-between gap-2">
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
                    className={linkBtnClass}
                    onClick={() => startEdit(status)}
                  >
                    Изменить
                  </button>
                  <button
                    type="button"
                    className={linkBtnClass}
                    onClick={() => void onDelete(status.id)}
                  >
                    Удалить
                  </button>
                </div>
              </div>
            )}
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
  const [renamingId, setRenamingId] = useState<number | null>(null);
  const [renameValue, setRenameValue] = useState("");

  const startRename = (field: CustomField) => {
    setRenamingId(field.id);
    setRenameValue(field.name);
  };

  const cancelRename = () => {
    setRenamingId(null);
    setRenameValue("");
  };

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
              <div className="min-w-0 flex-1">
                {renamingId === field.id ? (
                  <form
                    className="flex flex-wrap items-end gap-2"
                    onSubmit={(event) => {
                      event.preventDefault();
                      if (!renameValue.trim()) {
                        return;
                      }
                      void onUpdate(field.id, { name: renameValue.trim() }).then(cancelRename);
                    }}
                  >
                    <label className={`min-w-48 flex-1 ${labelClass}`}>
                      Название
                      <input
                        value={renameValue}
                        onChange={(event) => setRenameValue(event.target.value)}
                        className={inputClass}
                        required
                        autoFocus
                      />
                    </label>
                    <button type="submit" className={primaryBtnClass}>
                      Сохранить
                    </button>
                    <button
                      type="button"
                      onClick={cancelRename}
                      className="rounded-lg border border-border px-3 py-2 text-sm text-text-muted hover:text-text"
                    >
                      Отмена
                    </button>
                  </form>
                ) : (
                  <p className="font-medium text-text">{field.name}</p>
                )}
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
                {renamingId !== field.id && (
                  <button
                    type="button"
                    className={linkBtnClass}
                    onClick={() => startRename(field)}
                  >
                    Переименовать
                  </button>
                )}
                <button
                  type="button"
                  className={linkBtnClass}
                  onClick={() => void onDelete(field.id)}
                >
                  Удалить
                </button>
              </div>
            </div>

            {field.field_format === "list" && (
              <EnumerationEditor field={field} onUpdate={onUpdate} mode="flat" />
            )}

            {field.field_format === "link_list" && (
              <EnumerationEditor field={field} onUpdate={onUpdate} mode="linked" />
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
  const [newValue, setNewValue] = useState("");
  const [newCategory, setNewCategory] = useState("");
  const [childDrafts, setChildDrafts] = useState<Record<number, string>>({});

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
        </div>
        <form
          className="mt-2 flex flex-wrap items-center gap-2"
          onSubmit={(event) => {
            event.preventDefault();
            if (!newValue.trim()) {
              return;
            }
            void onUpdate(field.id, {
              enumerations: [
                ...field.enumerations,
                {
                  id: 0,
                  name: newValue.trim(),
                  position: field.enumerations.length,
                  is_active: true,
                  parent_id: null,
                },
              ],
            }).then(() => setNewValue(""));
          }}
        >
          <input
            value={newValue}
            onChange={(event) => setNewValue(event.target.value)}
            className="min-w-40 flex-1 rounded-lg border border-border px-2 py-1 text-xs text-text"
            placeholder="Новое значение"
          />
          <button type="submit" className="text-xs font-medium text-primary hover:underline">
            + значение
          </button>
        </form>
      </div>
    );
  }

  const parents = field.enumerations.filter((item) => !item.parent_id);

  return (
    <div className="mt-3 space-y-3">
      <p className="text-xs font-medium text-text-muted">Связанные списки</p>
      <form
        className="flex flex-wrap items-center gap-2"
        onSubmit={(event) => {
          event.preventDefault();
          if (!newCategory.trim()) {
            return;
          }
          void onUpdate(field.id, {
            enumerations: [
              ...field.enumerations,
              {
                id: 0,
                name: newCategory.trim(),
                position: parents.length,
                is_active: true,
                parent_id: null,
              },
            ],
          }).then(() => setNewCategory(""));
        }}
      >
        <input
          value={newCategory}
          onChange={(event) => setNewCategory(event.target.value)}
          className="min-w-40 flex-1 rounded-lg border border-border px-2 py-1 text-xs text-text"
          placeholder="Название категории"
        />
        <button type="submit" className="text-xs font-medium text-primary hover:underline">
          + категория
        </button>
      </form>
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
          </div>
          <form
            className="mt-2 flex flex-wrap items-center gap-2"
            onSubmit={(event) => {
              event.preventDefault();
              const value = (childDrafts[parent.id] ?? "").trim();
              if (!value) {
                return;
              }
              void onUpdate(field.id, {
                enumerations: [
                  ...field.enumerations,
                  {
                    id: 0,
                    name: value,
                    position: field.enumerations.filter(
                      (item) => item.parent_id === parent.id,
                    ).length,
                    is_active: true,
                    parent_id: parent.id,
                  },
                ],
              }).then(() =>
                setChildDrafts((prev) => ({ ...prev, [parent.id]: "" })),
              );
            }}
          >
            <input
              value={childDrafts[parent.id] ?? ""}
              onChange={(event) =>
                setChildDrafts((prev) => ({
                  ...prev,
                  [parent.id]: event.target.value,
                }))
              }
              className="min-w-40 flex-1 rounded-lg border border-border bg-surface px-2 py-1 text-xs text-text"
              placeholder={`Значение для «${parent.name}»`}
            />
            <button type="submit" className="text-xs font-medium text-primary hover:underline">
              + значение
            </button>
          </form>
        </div>
      ))}
    </div>
  );
}
