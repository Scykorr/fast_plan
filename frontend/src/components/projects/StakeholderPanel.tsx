import { useState, type FormEvent } from "react";

import type { RACIEntry, Stakeholder, WBSNode } from "../../api/projects";

export type StakeholderUpdateValues = {
  name: string;
  role: string;
  interest: number;
  influence: number;
  contact_email: string;
  notes: string;
};

type StakeholderPanelProps = {
  stakeholders: Stakeholder[];
  raci: RACIEntry[];
  wbs: WBSNode[];
  onAddStakeholder: (values: { name: string; role: string }) => Promise<void> | void;
  onUpdateStakeholder: (
    id: number,
    values: StakeholderUpdateValues,
  ) => Promise<void> | void;
  onDeleteStakeholder: (id: number) => void;
  onAddRACI: (values: {
    wbs_node_id: number;
    stakeholder_id: number;
    raci_type: "R" | "A" | "C" | "I";
  }) => Promise<void> | void;
  onDeleteRACI: (id: number) => void;
};

function flattenWBS(nodes: WBSNode[]): WBSNode[] {
  return nodes.flatMap((node) => [node, ...flattenWBS(node.children)]);
}

const inputClass =
  "w-full rounded-lg border border-border bg-cream px-3 py-2 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20";

function StakeholderEditForm({
  stakeholder,
  onSave,
  onCancel,
}: {
  stakeholder: Stakeholder;
  onSave: (values: StakeholderUpdateValues) => Promise<void> | void;
  onCancel: () => void;
}) {
  const [name, setName] = useState(stakeholder.name);
  const [role, setRole] = useState(stakeholder.role);
  const [interest, setInterest] = useState(stakeholder.interest);
  const [influence, setInfluence] = useState(stakeholder.influence);
  const [contactEmail, setContactEmail] = useState(stakeholder.contact_email);
  const [notes, setNotes] = useState(stakeholder.notes);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (!name.trim()) {
      setError("Укажите имя стейкхолдера");
      return;
    }
    setSaving(true);
    setError("");
    try {
      await onSave({
        name: name.trim(),
        role: role.trim(),
        interest,
        influence,
        contact_email: contactEmail.trim(),
        notes: notes.trim(),
      });
    } catch {
      setError("Не удалось сохранить стейкхолдера");
    } finally {
      setSaving(false);
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      noValidate
      className="mt-2 space-y-2 rounded-lg border border-dashed border-border bg-cream/40 p-3"
    >
      <div>
        <label
          htmlFor={`stakeholder-edit-name-${stakeholder.id}`}
          className="mb-1 block text-xs font-medium"
        >
          Имя
        </label>
        <input
          id={`stakeholder-edit-name-${stakeholder.id}`}
          value={name}
          onChange={(e) => setName(e.target.value)}
          className={inputClass}
          autoFocus
        />
      </div>
      <div>
        <label
          htmlFor={`stakeholder-edit-role-${stakeholder.id}`}
          className="mb-1 block text-xs font-medium"
        >
          Роль
        </label>
        <input
          id={`stakeholder-edit-role-${stakeholder.id}`}
          value={role}
          onChange={(e) => setRole(e.target.value)}
          className={inputClass}
        />
      </div>
      <div className="grid gap-2 sm:grid-cols-2">
        <div>
          <label
            htmlFor={`stakeholder-edit-interest-${stakeholder.id}`}
            className="mb-1 block text-xs font-medium"
          >
            Интерес
          </label>
          <select
            id={`stakeholder-edit-interest-${stakeholder.id}`}
            value={interest}
            onChange={(e) => setInterest(Number(e.target.value))}
            className={inputClass}
          >
            {[1, 2, 3, 4, 5].map((level) => (
              <option key={level} value={level}>
                {level}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label
            htmlFor={`stakeholder-edit-influence-${stakeholder.id}`}
            className="mb-1 block text-xs font-medium"
          >
            Влияние
          </label>
          <select
            id={`stakeholder-edit-influence-${stakeholder.id}`}
            value={influence}
            onChange={(e) => setInfluence(Number(e.target.value))}
            className={inputClass}
          >
            {[1, 2, 3, 4, 5].map((level) => (
              <option key={level} value={level}>
                {level}
              </option>
            ))}
          </select>
        </div>
      </div>
      <div>
        <label
          htmlFor={`stakeholder-edit-email-${stakeholder.id}`}
          className="mb-1 block text-xs font-medium"
        >
          Email
        </label>
        <input
          id={`stakeholder-edit-email-${stakeholder.id}`}
          type="email"
          value={contactEmail}
          onChange={(e) => setContactEmail(e.target.value)}
          className={inputClass}
        />
      </div>
      <div>
        <label
          htmlFor={`stakeholder-edit-notes-${stakeholder.id}`}
          className="mb-1 block text-xs font-medium"
        >
          Заметки
        </label>
        <textarea
          id={`stakeholder-edit-notes-${stakeholder.id}`}
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          rows={2}
          className={inputClass}
        />
      </div>
      {error && (
        <p className="text-xs text-primary" role="alert">
          {error}
        </p>
      )}
      <div className="flex gap-2">
        <button
          type="submit"
          disabled={saving}
          className="rounded-lg bg-primary px-3 py-1.5 text-xs font-semibold text-white hover:bg-primary-hover disabled:opacity-60"
        >
          {saving ? "Сохранение..." : "Сохранить"}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="rounded-lg border border-border px-3 py-1.5 text-xs text-text-muted hover:bg-cream"
        >
          Отмена
        </button>
      </div>
    </form>
  );
}

export function StakeholderPanel({
  stakeholders,
  raci,
  wbs,
  onAddStakeholder,
  onUpdateStakeholder,
  onDeleteStakeholder,
  onAddRACI,
  onDeleteRACI,
}: StakeholderPanelProps) {
  const wbsNodes = flattenWBS(wbs);
  const [showStakeholderForm, setShowStakeholderForm] = useState(false);
  const [showRaciForm, setShowRaciForm] = useState(false);
  const [name, setName] = useState("");
  const [role, setRole] = useState("");
  const [wbsNodeId, setWbsNodeId] = useState<number | "">("");
  const [stakeholderId, setStakeholderId] = useState<number | "">("");
  const [raciType, setRaciType] = useState<"R" | "A" | "C" | "I">("R");
  const [stakeholderError, setStakeholderError] = useState("");
  const [raciError, setRaciError] = useState("");
  const [loadingStakeholder, setLoadingStakeholder] = useState(false);
  const [loadingRaci, setLoadingRaci] = useState(false);
  const [editingStakeholderId, setEditingStakeholderId] = useState<number | null>(null);

  const handleStakeholderSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (!name.trim()) {
      setStakeholderError("Укажите имя стейкхолдера");
      return;
    }
    setLoadingStakeholder(true);
    setStakeholderError("");
    try {
      await onAddStakeholder({ name: name.trim(), role: role.trim() });
      setName("");
      setRole("");
      setShowStakeholderForm(false);
    } catch {
      setStakeholderError("Не удалось добавить стейкхолдера");
    } finally {
      setLoadingStakeholder(false);
    }
  };

  const handleRaciSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (wbsNodeId === "" || stakeholderId === "") {
      setRaciError("Выберите WBS-узел и стейкхолдера");
      return;
    }
    setLoadingRaci(true);
    setRaciError("");
    try {
      await onAddRACI({
        wbs_node_id: Number(wbsNodeId),
        stakeholder_id: Number(stakeholderId),
        raci_type: raciType,
      });
      setShowRaciForm(false);
      setRaciType("R");
    } catch {
      setRaciError("Не удалось создать назначение RACI");
    } finally {
      setLoadingRaci(false);
    }
  };

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <div className="rounded-xl border border-border bg-surface p-4">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-text">Стейкхолдеры</h2>
          <button
            type="button"
            onClick={() => setShowStakeholderForm((value) => !value)}
            className="text-sm font-medium text-primary hover:underline"
          >
            {showStakeholderForm ? "Скрыть" : "+ Добавить"}
          </button>
        </div>

        {showStakeholderForm && (
          <form
            onSubmit={handleStakeholderSubmit}
            noValidate
            className="mb-4 space-y-3 rounded-lg border border-dashed border-border p-3"
          >
            <div>
              <label htmlFor="stakeholder-name" className="mb-1 block text-sm font-medium">
                Имя
              </label>
              <input
                id="stakeholder-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className={inputClass}
                autoFocus
              />
            </div>
            <div>
              <label htmlFor="stakeholder-role" className="mb-1 block text-sm font-medium">
                Роль
              </label>
              <input
                id="stakeholder-role"
                value={role}
                onChange={(e) => setRole(e.target.value)}
                className={inputClass}
              />
            </div>
            {stakeholderError && (
              <p className="text-sm text-primary" role="alert">
                {stakeholderError}
              </p>
            )}
            <button
              type="submit"
              disabled={loadingStakeholder}
              className="rounded-lg bg-primary px-3 py-1.5 text-sm font-semibold text-white hover:bg-primary-hover disabled:opacity-60"
            >
              {loadingStakeholder ? "Сохранение..." : "Сохранить"}
            </button>
          </form>
        )}

        {stakeholders.length === 0 ? (
          <p className="text-sm text-text-muted">Список пуст</p>
        ) : (
          <ul className="space-y-2">
            {stakeholders.map((item) => (
              <li
                key={item.id}
                className="rounded-lg border border-border px-3 py-2 text-sm"
              >
                <div className="flex justify-between gap-2">
                  <div>
                    <p className="font-medium">{item.name}</p>
                    <p className="text-xs text-text-muted">
                      {item.role || "—"} · интерес {item.interest} · влияние{" "}
                      {item.influence}
                    </p>
                    {item.contact_email && (
                      <p className="text-xs text-text-muted">{item.contact_email}</p>
                    )}
                    {item.notes && (
                      <p className="mt-1 text-xs text-text-muted">{item.notes}</p>
                    )}
                  </div>
                  <div className="flex shrink-0 gap-2">
                    <button
                      type="button"
                      onClick={() =>
                        setEditingStakeholderId((current) =>
                          current === item.id ? null : item.id,
                        )
                      }
                      className="text-xs text-text-muted hover:text-primary"
                    >
                      {editingStakeholderId === item.id ? "Скрыть" : "Изменить"}
                    </button>
                    <button
                      type="button"
                      onClick={() => onDeleteStakeholder(item.id)}
                      className="text-xs text-text-muted hover:text-primary"
                    >
                      ×
                    </button>
                  </div>
                </div>
                {editingStakeholderId === item.id && (
                  <StakeholderEditForm
                    stakeholder={item}
                    onSave={async (values) => {
                      await onUpdateStakeholder(item.id, values);
                      setEditingStakeholderId(null);
                    }}
                    onCancel={() => setEditingStakeholderId(null)}
                  />
                )}
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="rounded-xl border border-border bg-surface p-4">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-text">RACI-матрица</h2>
          <button
            type="button"
            onClick={() => {
              setShowRaciForm((value) => !value);
              if (wbsNodes[0] && wbsNodeId === "") {
                setWbsNodeId(wbsNodes[0].id);
              }
              if (stakeholders[0] && stakeholderId === "") {
                setStakeholderId(stakeholders[0].id);
              }
            }}
            disabled={stakeholders.length === 0 || wbsNodes.length === 0}
            className="text-sm font-medium text-primary hover:underline disabled:opacity-50"
          >
            {showRaciForm ? "Скрыть" : "+ Назначение"}
          </button>
        </div>

        {showRaciForm && (
          <form
            onSubmit={handleRaciSubmit}
            noValidate
            className="mb-4 space-y-3 rounded-lg border border-dashed border-border p-3"
          >
            <div>
              <label htmlFor="raci-wbs" className="mb-1 block text-sm font-medium">
                WBS
              </label>
              <select
                id="raci-wbs"
                value={wbsNodeId}
                onChange={(e) => setWbsNodeId(Number(e.target.value))}
                className={inputClass}
              >
                {wbsNodes.map((node) => (
                  <option key={node.id} value={node.id}>
                    {node.code} {node.title}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="raci-stakeholder" className="mb-1 block text-sm font-medium">
                Стейкхолдер
              </label>
              <select
                id="raci-stakeholder"
                value={stakeholderId}
                onChange={(e) => setStakeholderId(Number(e.target.value))}
                className={inputClass}
              >
                {stakeholders.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="raci-type" className="mb-1 block text-sm font-medium">
                Тип RACI
              </label>
              <select
                id="raci-type"
                value={raciType}
                onChange={(e) => setRaciType(e.target.value as "R" | "A" | "C" | "I")}
                className={inputClass}
              >
                <option value="R">R — Responsible</option>
                <option value="A">A — Accountable</option>
                <option value="C">C — Consulted</option>
                <option value="I">I — Informed</option>
              </select>
            </div>
            {raciError && (
              <p className="text-sm text-primary" role="alert">
                {raciError}
              </p>
            )}
            <button
              type="submit"
              disabled={loadingRaci}
              className="rounded-lg bg-primary px-3 py-1.5 text-sm font-semibold text-white hover:bg-primary-hover disabled:opacity-60"
            >
              {loadingRaci ? "Сохранение..." : "Сохранить"}
            </button>
          </form>
        )}

        {raci.length === 0 ? (
          <p className="text-sm text-text-muted">Назначения не созданы</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-text-muted">
                  <th className="py-2 pr-3">WBS</th>
                  <th className="py-2 pr-3">Стейкхолдер</th>
                  <th className="py-2">RACI</th>
                  <th className="py-2" />
                </tr>
              </thead>
              <tbody>
                {raci.map((entry) => (
                  <tr key={entry.id} className="border-b border-border/60">
                    <td className="py-2 pr-3 font-mono text-xs">
                      {entry.wbs_code}
                    </td>
                    <td className="py-2 pr-3">{entry.stakeholder_name}</td>
                    <td className="py-2 font-semibold text-secondary">
                      {entry.raci_type}
                    </td>
                    <td className="py-2 text-right">
                      <button
                        type="button"
                        onClick={() => onDeleteRACI(entry.id)}
                        className="text-xs text-text-muted hover:text-primary"
                      >
                        ×
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
