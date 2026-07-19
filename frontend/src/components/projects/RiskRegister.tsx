import { useState, type FormEvent } from "react";

import type { Risk } from "../../api/projects";

type RiskHeatMapProps = {
  risks: Risk[];
};

export function RiskHeatMap({ risks }: RiskHeatMapProps) {
  const levels = [1, 2, 3, 4, 5];

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[280px] border-collapse text-center text-xs">
        <thead>
          <tr>
            <th className="p-2 text-left text-text-muted">Влияние →</th>
            {levels.map((level) => (
              <th key={level} className="p-2 text-text-muted">
                {level}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {levels.map((impact) => (
            <tr key={impact}>
              <td className="p-2 text-left font-medium text-text">{impact}</td>
              {levels.map((probability) => {
                const count = risks.filter(
                  (risk) => risk.probability === probability && risk.impact === impact,
                ).length;
                const score = probability * impact;
                const tone =
                  score >= 15
                    ? "bg-primary/20 text-primary"
                    : score >= 9
                      ? "bg-accent/30 text-text"
                      : "bg-cream text-text-muted";
                return (
                  <td key={probability} className="p-1">
                    <div
                      className={`rounded-md py-3 font-semibold ${tone}`}
                      title={`P${probability} × I${impact}`}
                    >
                      {count || "·"}
                    </div>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-2 text-xs text-text-muted">Вероятность ↓ по строкам</p>
    </div>
  );
}

export type RiskFormValues = {
  title: string;
  probability: number;
  impact: number;
};

export type RiskUpdateValues = {
  title: string;
  description: string;
  status: string;
  mitigation: string;
  probability: number;
  impact: number;
};

const RISK_STATUSES = [
  { value: "open", label: "Открыт" },
  { value: "mitigated", label: "Смягчён" },
  { value: "closed", label: "Закрыт" },
];

type RiskRegisterProps = {
  risks: Risk[];
  highlightedRiskId?: number | null;
  onAdd: (values: RiskFormValues) => Promise<void> | void;
  onUpdate: (id: number, values: RiskUpdateValues) => Promise<void> | void;
  onDelete: (id: number) => void;
};

const inputClass =
  "w-full rounded-lg border border-border bg-cream px-3 py-2 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20";

function RiskEditForm({
  risk,
  onSave,
  onCancel,
}: {
  risk: Risk;
  onSave: (values: RiskUpdateValues) => Promise<void> | void;
  onCancel: () => void;
}) {
  const [title, setTitle] = useState(risk.title);
  const [description, setDescription] = useState(risk.description);
  const [status, setStatus] = useState(risk.status);
  const [mitigation, setMitigation] = useState(risk.mitigation);
  const [probability, setProbability] = useState(risk.probability);
  const [impact, setImpact] = useState(risk.impact);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (!title.trim()) {
      setError("Укажите название риска");
      return;
    }
    setSaving(true);
    setError("");
    try {
      await onSave({
        title: title.trim(),
        description: description.trim(),
        status,
        mitigation: mitigation.trim(),
        probability,
        impact,
      });
    } catch {
      setError("Не удалось сохранить риск");
    } finally {
      setSaving(false);
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      noValidate
      className="mt-3 space-y-3 rounded-lg border border-dashed border-border bg-cream/40 p-3"
    >
      <div>
        <label htmlFor={`risk-edit-title-${risk.id}`} className="mb-1 block text-sm font-medium">
          Название
        </label>
        <input
          id={`risk-edit-title-${risk.id}`}
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          className={inputClass}
          autoFocus
        />
      </div>
      <div>
        <label htmlFor={`risk-edit-description-${risk.id}`} className="mb-1 block text-sm font-medium">
          Описание
        </label>
        <textarea
          id={`risk-edit-description-${risk.id}`}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={2}
          className={inputClass}
        />
      </div>
      <div className="grid gap-3 sm:grid-cols-3">
        <div>
          <label htmlFor={`risk-edit-probability-${risk.id}`} className="mb-1 block text-sm font-medium">
            Вероятность
          </label>
          <select
            id={`risk-edit-probability-${risk.id}`}
            value={probability}
            onChange={(e) => setProbability(Number(e.target.value))}
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
          <label htmlFor={`risk-edit-impact-${risk.id}`} className="mb-1 block text-sm font-medium">
            Влияние
          </label>
          <select
            id={`risk-edit-impact-${risk.id}`}
            value={impact}
            onChange={(e) => setImpact(Number(e.target.value))}
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
          <label htmlFor={`risk-edit-status-${risk.id}`} className="mb-1 block text-sm font-medium">
            Статус
          </label>
          <select
            id={`risk-edit-status-${risk.id}`}
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className={inputClass}
          >
            {RISK_STATUSES.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
        </div>
      </div>
      <div>
        <label htmlFor={`risk-edit-mitigation-${risk.id}`} className="mb-1 block text-sm font-medium">
          Митигация
        </label>
        <textarea
          id={`risk-edit-mitigation-${risk.id}`}
          value={mitigation}
          onChange={(e) => setMitigation(e.target.value)}
          rows={2}
          className={inputClass}
        />
      </div>
      {error && (
        <p className="text-sm text-primary" role="alert">
          {error}
        </p>
      )}
      <div className="flex gap-2">
        <button
          type="submit"
          disabled={saving}
          className="rounded-lg bg-primary px-3 py-1.5 text-sm font-semibold text-white hover:bg-primary-hover disabled:opacity-60"
        >
          {saving ? "Сохранение..." : "Сохранить"}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="rounded-lg border border-border px-3 py-1.5 text-sm text-text-muted hover:bg-cream"
        >
          Отмена
        </button>
      </div>
    </form>
  );
}

export function RiskRegister({
  risks,
  highlightedRiskId = null,
  onAdd,
  onUpdate,
  onDelete,
}: RiskRegisterProps) {
  const [showForm, setShowForm] = useState(false);
  const [title, setTitle] = useState("");
  const [probability, setProbability] = useState(3);
  const [impact, setImpact] = useState(3);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);

  const resetForm = () => {
    setTitle("");
    setProbability(3);
    setImpact(3);
    setError("");
    setShowForm(false);
  };

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (!title.trim()) {
      setError("Укажите название риска");
      return;
    }
    setLoading(true);
    setError("");
    try {
      await onAdd({
        title: title.trim(),
        probability,
        impact,
      });
      resetForm();
    } catch {
      setError("Не удалось создать риск");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-text">Реестр рисков</h2>
        <button
          type="button"
          onClick={() => setShowForm((value) => !value)}
          className="rounded-lg bg-primary px-3 py-1.5 text-sm font-semibold text-white hover:bg-primary-hover"
        >
          {showForm ? "Скрыть" : "+ Риск"}
        </button>
      </div>

      {showForm && (
        <form
          onSubmit={handleSubmit}
          noValidate
          className="space-y-3 rounded-xl border border-dashed border-border bg-surface p-4"
        >
          <div>
            <label htmlFor="risk-title" className="mb-1 block text-sm font-medium">
              Название
            </label>
            <input
              id="risk-title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className={inputClass}
              autoFocus
            />
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label htmlFor="risk-probability" className="mb-1 block text-sm font-medium">
                Вероятность
              </label>
              <select
                id="risk-probability"
                value={probability}
                onChange={(e) => setProbability(Number(e.target.value))}
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
              <label htmlFor="risk-impact" className="mb-1 block text-sm font-medium">
                Влияние
              </label>
              <select
                id="risk-impact"
                value={impact}
                onChange={(e) => setImpact(Number(e.target.value))}
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
          {error && (
            <p className="text-sm text-primary" role="alert">
              {error}
            </p>
          )}
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={loading}
              className="rounded-lg bg-primary px-3 py-1.5 text-sm font-semibold text-white hover:bg-primary-hover disabled:opacity-60"
            >
              {loading ? "Сохранение..." : "Добавить"}
            </button>
            <button
              type="button"
              onClick={resetForm}
              className="rounded-lg border border-border px-3 py-1.5 text-sm text-text-muted hover:bg-cream"
            >
              Отмена
            </button>
          </div>
        </form>
      )}

      <RiskHeatMap risks={risks} />
      {risks.length === 0 ? (
        <p className="text-sm text-text-muted">Риски не зарегистрированы</p>
      ) : (
        <ul className="space-y-2">
          {risks.map((risk) => (
            <li
              key={risk.id}
              id={`risk-${risk.id}`}
              data-highlighted={
                highlightedRiskId === risk.id ? "true" : undefined
              }
              className={[
                "rounded-lg border bg-surface px-4 py-3",
                highlightedRiskId === risk.id
                  ? "border-primary ring-2 ring-primary/40"
                  : "border-border",
              ].join(" ")}
            >
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="font-medium text-text">{risk.title}</p>
                  <p className="mt-1 text-xs text-text-muted">
                    P{risk.probability} × I{risk.impact} = {risk.score} · {risk.status}
                  </p>
                  {risk.description && (
                    <p className="mt-1 text-xs text-text-muted">{risk.description}</p>
                  )}
                  {risk.mitigation && (
                    <p className="mt-1 text-xs text-secondary">
                      Митигация: {risk.mitigation}
                    </p>
                  )}
                </div>
                <div className="flex shrink-0 gap-3">
                  <button
                    type="button"
                    onClick={() =>
                      setEditingId((current) => (current === risk.id ? null : risk.id))
                    }
                    className="text-sm text-text-muted hover:text-primary"
                  >
                    {editingId === risk.id ? "Скрыть" : "Изменить"}
                  </button>
                  <button
                    type="button"
                    onClick={() => onDelete(risk.id)}
                    className="text-sm text-text-muted hover:text-primary"
                  >
                    Удалить
                  </button>
                </div>
              </div>
              {editingId === risk.id && (
                <RiskEditForm
                  risk={risk}
                  onSave={async (values) => {
                    await onUpdate(risk.id, values);
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
