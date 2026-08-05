import { useState, type FormEvent } from "react";

import type { ProjectIssue, Risk } from "../../api/projects";
import type { WorkspaceMember } from "../../api/workspace";

export type IssueFormValues = {
  title: string;
  issue_type: string;
  priority: string;
  owner_id: number | null;
  due_date: string;
};

export type IssueUpdateValues = {
  title: string;
  description: string;
  issue_type: string;
  priority: string;
  status: string;
  owner_id: number | null;
  due_date: string | null;
  action: string;
  related_risk_id: number | null;
};

const ISSUE_TYPES = [
  { value: "problem", label: "Проблема / off-spec" },
  { value: "request", label: "Запрос на изменение" },
  { value: "other", label: "Прочее" },
];

const PRIORITIES = [
  { value: "high", label: "Высокий" },
  { value: "medium", label: "Средний" },
  { value: "low", label: "Низкий" },
];

const STATUSES = [
  { value: "open", label: "Открыт" },
  { value: "in_progress", label: "В работе" },
  { value: "resolved", label: "Решён" },
  { value: "closed", label: "Закрыт" },
];

type IssueRegisterProps = {
  issues: ProjectIssue[];
  risks: Risk[];
  members: WorkspaceMember[];
  onAdd: (values: IssueFormValues) => Promise<void> | void;
  onUpdate: (id: number, values: IssueUpdateValues) => Promise<void> | void;
  onDelete: (id: number) => void;
};

const inputClass =
  "w-full rounded-lg border border-border bg-cream px-3 py-2 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20";

function priorityTone(priority: string): string {
  if (priority === "high") return "text-red-700";
  if (priority === "low") return "text-text-muted";
  return "text-amber-800";
}

function IssueEditForm({
  issue,
  risks,
  members,
  onSave,
  onCancel,
}: {
  issue: ProjectIssue;
  risks: Risk[];
  members: WorkspaceMember[];
  onSave: (values: IssueUpdateValues) => Promise<void> | void;
  onCancel: () => void;
}) {
  const [title, setTitle] = useState(issue.title);
  const [description, setDescription] = useState(issue.description);
  const [issueType, setIssueType] = useState(issue.issue_type);
  const [priority, setPriority] = useState(issue.priority);
  const [status, setStatus] = useState(issue.status);
  const [ownerId, setOwnerId] = useState<string>(
    issue.owner_id != null ? String(issue.owner_id) : "",
  );
  const [dueDate, setDueDate] = useState(issue.due_date ?? "");
  const [action, setAction] = useState(issue.action);
  const [relatedRiskId, setRelatedRiskId] = useState<string>(
    issue.related_risk_id != null ? String(issue.related_risk_id) : "",
  );
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (!title.trim()) {
      setError("Укажите название");
      return;
    }
    setSaving(true);
    setError("");
    try {
      await onSave({
        title: title.trim(),
        description: description.trim(),
        issue_type: issueType,
        priority,
        status,
        owner_id: ownerId ? Number(ownerId) : null,
        due_date: dueDate || null,
        action: action.trim(),
        related_risk_id: relatedRiskId ? Number(relatedRiskId) : null,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось сохранить");
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={(e) => void handleSubmit(e)} className="mt-3 space-y-2">
      <input
        className={inputClass}
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="Название"
      />
      <textarea
        className={inputClass}
        rows={2}
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        placeholder="Описание"
      />
      <div className="grid gap-2 sm:grid-cols-2">
        <select
          className={inputClass}
          value={issueType}
          onChange={(e) => setIssueType(e.target.value)}
        >
          {ISSUE_TYPES.map((t) => (
            <option key={t.value} value={t.value}>
              {t.label}
            </option>
          ))}
        </select>
        <select
          className={inputClass}
          value={priority}
          onChange={(e) => setPriority(e.target.value)}
        >
          {PRIORITIES.map((p) => (
            <option key={p.value} value={p.value}>
              {p.label}
            </option>
          ))}
        </select>
        <select
          className={inputClass}
          value={status}
          onChange={(e) => setStatus(e.target.value)}
        >
          {STATUSES.map((s) => (
            <option key={s.value} value={s.value}>
              {s.label}
            </option>
          ))}
        </select>
        <select
          className={inputClass}
          value={ownerId}
          onChange={(e) => setOwnerId(e.target.value)}
        >
          <option value="">Без владельца</option>
          {members.map((m) => (
            <option key={m.user_id} value={m.user_id}>
              {m.email || m.username}
            </option>
          ))}
        </select>
        <input
          type="date"
          className={inputClass}
          value={dueDate}
          onChange={(e) => setDueDate(e.target.value)}
        />
        <select
          className={inputClass}
          value={relatedRiskId}
          onChange={(e) => setRelatedRiskId(e.target.value)}
        >
          <option value="">Связанный риск — нет</option>
          {risks.map((r) => (
            <option key={r.id} value={r.id}>
              #{r.id} · {r.title}
            </option>
          ))}
        </select>
      </div>
      <textarea
        className={inputClass}
        rows={2}
        value={action}
        onChange={(e) => setAction(e.target.value)}
        placeholder="Следующее действие / решение"
      />
      {error && <p className="text-xs text-red-700">{error}</p>}
      <div className="flex gap-2">
        <button
          type="submit"
          disabled={saving}
          className="rounded-lg bg-primary px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-60"
        >
          Сохранить
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="rounded-lg border border-border px-3 py-1.5 text-sm"
        >
          Отмена
        </button>
      </div>
    </form>
  );
}

export function IssueRegister({
  issues,
  risks,
  members,
  onAdd,
  onUpdate,
  onDelete,
}: IssueRegisterProps) {
  const [title, setTitle] = useState("");
  const [issueType, setIssueType] = useState("problem");
  const [priority, setPriority] = useState("medium");
  const [ownerId, setOwnerId] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [filterOpen, setFilterOpen] = useState(true);
  const [addError, setAddError] = useState("");

  const visible = filterOpen
    ? issues.filter((i) => i.status === "open" || i.status === "in_progress")
    : issues;

  const handleAdd = async (event: FormEvent) => {
    event.preventDefault();
    if (!title.trim()) {
      setAddError("Укажите название");
      return;
    }
    setAddError("");
    try {
      await onAdd({
        title: title.trim(),
        issue_type: issueType,
        priority,
        owner_id: ownerId ? Number(ownerId) : null,
        due_date: dueDate,
      });
      setTitle("");
      setDueDate("");
    } catch (err) {
      setAddError(err instanceof Error ? err.message : "Не удалось создать");
    }
  };

  return (
    <div className="space-y-4">
      <p className="text-sm text-text-muted">
        Issue / action log (PRINCE2) — отдельно от реестра рисков: проблемы,
        запросы на изменение, действия с владельцем и сроком.
      </p>

      <form
        onSubmit={(e) => void handleAdd(e)}
        className="grid gap-2 rounded-xl border border-border bg-surface p-4 sm:grid-cols-2 lg:grid-cols-6"
      >
        <input
          className={`${inputClass} lg:col-span-2`}
          placeholder="Новый issue…"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
        <select
          className={inputClass}
          value={issueType}
          onChange={(e) => setIssueType(e.target.value)}
        >
          {ISSUE_TYPES.map((t) => (
            <option key={t.value} value={t.value}>
              {t.label}
            </option>
          ))}
        </select>
        <select
          className={inputClass}
          value={priority}
          onChange={(e) => setPriority(e.target.value)}
        >
          {PRIORITIES.map((p) => (
            <option key={p.value} value={p.value}>
              {p.label}
            </option>
          ))}
        </select>
        <select
          className={inputClass}
          value={ownerId}
          onChange={(e) => setOwnerId(e.target.value)}
        >
          <option value="">Владелец</option>
          {members.map((m) => (
            <option key={m.user_id} value={m.user_id}>
              {m.email || m.username}
            </option>
          ))}
        </select>
        <div className="flex gap-2">
          <input
            type="date"
            className={inputClass}
            value={dueDate}
            onChange={(e) => setDueDate(e.target.value)}
          />
          <button
            type="submit"
            className="shrink-0 rounded-lg bg-primary px-3 py-2 text-sm font-semibold text-white"
          >
            +
          </button>
        </div>
        {addError && (
          <p className="text-xs text-red-700 sm:col-span-2 lg:col-span-6">
            {addError}
          </p>
        )}
      </form>

      <label className="flex items-center gap-2 text-sm text-text-muted">
        <input
          type="checkbox"
          checked={filterOpen}
          onChange={(e) => setFilterOpen(e.target.checked)}
        />
        Только открытые / в работе
      </label>

      {visible.length === 0 ? (
        <p className="text-sm text-text-muted">Нет issues</p>
      ) : (
        <ul className="space-y-3">
          {visible.map((issue) => (
            <li
              key={issue.id}
              className="rounded-xl border border-border bg-surface p-4"
            >
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <p className="font-semibold text-text">{issue.title}</p>
                  <p className="mt-0.5 text-xs text-text-muted">
                    <span className={priorityTone(issue.priority)}>
                      {PRIORITIES.find((p) => p.value === issue.priority)?.label ||
                        issue.priority}
                    </span>
                    {" · "}
                    {ISSUE_TYPES.find((t) => t.value === issue.issue_type)?.label ||
                      issue.issue_type}
                    {" · "}
                    {STATUSES.find((s) => s.value === issue.status)?.label ||
                      issue.status}
                    {issue.owner_name ? ` · ${issue.owner_name}` : ""}
                    {issue.due_date ? ` · due ${issue.due_date}` : ""}
                    {issue.related_risk_id
                      ? ` · risk #${issue.related_risk_id}`
                      : ""}
                  </p>
                  {issue.action && (
                    <p className="mt-1 text-sm text-text">{issue.action}</p>
                  )}
                </div>
                <div className="flex gap-2">
                  <button
                    type="button"
                    className="text-xs text-primary hover:underline"
                    onClick={() =>
                      setEditingId(editingId === issue.id ? null : issue.id)
                    }
                  >
                    {editingId === issue.id ? "Свернуть" : "Изменить"}
                  </button>
                  <button
                    type="button"
                    className="text-xs text-text-muted hover:text-red-700"
                    onClick={() => onDelete(issue.id)}
                  >
                    Удалить
                  </button>
                </div>
              </div>
              {editingId === issue.id && (
                <IssueEditForm
                  issue={issue}
                  risks={risks}
                  members={members}
                  onSave={async (values) => {
                    await onUpdate(issue.id, values);
                    setEditingId(null);
                  }}
                  onCancel={() => setEditingId(null)}
                />
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
