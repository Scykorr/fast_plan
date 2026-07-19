import { type FormEvent, useState } from "react";

import { parseApiError } from "../../api/errors";
import type { Project } from "../../api/projects";

const inputClass =
  "w-full rounded-lg border border-border bg-cream px-3 py-2 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20";

export type TransactionFormValues = {
  title: string;
  amount: string;
  transaction_type: "expense" | "income";
  transaction_date: string;
  category: string;
  notes: string;
  project_id: number | null;
};

type TransactionFormProps = {
  projects: Project[];
  initial?: Partial<TransactionFormValues>;
  submitLabel?: string;
  onSubmit: (values: TransactionFormValues) => Promise<void>;
  onCancel?: () => void;
};

export function TransactionForm({
  projects,
  initial,
  submitLabel = "Сохранить",
  onSubmit,
  onCancel,
}: TransactionFormProps) {
  const [values, setValues] = useState<TransactionFormValues>({
    title: initial?.title ?? "",
    amount: initial?.amount ?? "",
    transaction_type: initial?.transaction_type ?? "expense",
    transaction_date:
      initial?.transaction_date ?? new Date().toISOString().slice(0, 10),
    category: initial?.category ?? "",
    notes: initial?.notes ?? "",
    project_id: initial?.project_id ?? null,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (!values.title.trim()) {
      setError("Укажите название");
      return;
    }
    if (!values.amount || Number(values.amount) <= 0) {
      setError("Укажите положительную сумму");
      return;
    }
    setError("");
    setLoading(true);
    try {
      await onSubmit({
        ...values,
        title: values.title.trim(),
        category: values.category.trim(),
        notes: values.notes.trim(),
      });
    } catch (err) {
      setError(parseApiError(err, "Не удалось сохранить транзакцию"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <form
      noValidate
      onSubmit={(event) => void handleSubmit(event)}
      className="rounded-xl border border-border bg-surface p-5"
    >
      <h2 className="text-lg font-semibold text-text">Транзакция</h2>
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <label className="text-sm">
          <span className="mb-1 block text-text-muted">Название</span>
          <input
            aria-label="Название"
            required
            className={inputClass}
            value={values.title}
            onChange={(event) =>
              setValues((prev) => ({ ...prev, title: event.target.value }))
            }
          />
        </label>
        <label className="text-sm">
          <span className="mb-1 block text-text-muted">Сумма</span>
          <input
            aria-label="Сумма"
            required
            type="number"
            min="0.01"
            step="0.01"
            className={inputClass}
            value={values.amount}
            onChange={(event) =>
              setValues((prev) => ({ ...prev, amount: event.target.value }))
            }
          />
        </label>
        <label className="text-sm">
          <span className="mb-1 block text-text-muted">Тип</span>
          <select
            aria-label="Тип"
            className={inputClass}
            value={values.transaction_type}
            onChange={(event) =>
              setValues((prev) => ({
                ...prev,
                transaction_type: event.target.value as "expense" | "income",
              }))
            }
          >
            <option value="expense">Расход</option>
            <option value="income">Доход</option>
          </select>
        </label>
        <label className="text-sm">
          <span className="mb-1 block text-text-muted">Дата</span>
          <input
            aria-label="Дата"
            required
            type="date"
            className={inputClass}
            value={values.transaction_date}
            onChange={(event) =>
              setValues((prev) => ({
                ...prev,
                transaction_date: event.target.value,
              }))
            }
          />
        </label>
        <label className="text-sm">
          <span className="mb-1 block text-text-muted">Категория</span>
          <input
            aria-label="Категория"
            className={inputClass}
            value={values.category}
            onChange={(event) =>
              setValues((prev) => ({ ...prev, category: event.target.value }))
            }
          />
        </label>
        <label className="text-sm">
          <span className="mb-1 block text-text-muted">Проект</span>
          <select
            aria-label="Проект"
            className={inputClass}
            value={values.project_id ?? ""}
            onChange={(event) =>
              setValues((prev) => ({
                ...prev,
                project_id: event.target.value
                  ? Number(event.target.value)
                  : null,
              }))
            }
          >
            <option value="">Без проекта</option>
            {projects.map((project) => (
              <option key={project.id} value={project.id}>
                {project.name}
              </option>
            ))}
          </select>
        </label>
        <label className="sm:col-span-2 text-sm">
          <span className="mb-1 block text-text-muted">Заметки</span>
          <textarea
            aria-label="Заметки"
            rows={2}
            className={inputClass}
            value={values.notes}
            onChange={(event) =>
              setValues((prev) => ({ ...prev, notes: event.target.value }))
            }
          />
        </label>
      </div>
      {error && (
        <p className="mt-3 text-sm text-primary" role="alert">
          {error}
        </p>
      )}
      <div className="mt-4 flex gap-2">
        <button
          type="submit"
          disabled={loading}
          className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary-hover disabled:opacity-60"
        >
          {loading ? "Сохранение..." : submitLabel}
        </button>
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            className="rounded-lg border border-border px-4 py-2 text-sm text-text-muted hover:bg-cream"
          >
            Отмена
          </button>
        )}
      </div>
    </form>
  );
}
