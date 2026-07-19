import { useCallback, useEffect, useState } from "react";

import { parseApiError } from "../api/errors";
import type { Transaction } from "../api/finance";
import type { Project } from "../api/projects";
import { ErrorMessage } from "../components/ErrorMessage";
import {
  TransactionForm,
  type TransactionFormValues,
} from "../components/finance/TransactionForm";
import { useFinanceApi } from "../hooks/useFinanceApi";
import { useProjectsApi } from "../hooks/useProjectsApi";
import { useWorkspace } from "../context/WorkspaceContext";

export function FinancePage() {
  const financeApi = useFinanceApi();
  const projectsApi = useProjectsApi();
  const { workspaceEpoch } = useWorkspace();
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Transaction | null>(null);

  const load = useCallback(async () => {
    if (!financeApi || !projectsApi) {
      return;
    }
    try {
      const [items, projectItems] = await Promise.all([
        financeApi.getTransactions(),
        projectsApi.getProjects(),
      ]);
      setTransactions(items);
      setProjects(projectItems);
    } catch (err) {
      setError(parseApiError(err, "Не удалось загрузить транзакции"));
    }
  }, [financeApi, projectsApi]);

  useEffect(() => {
    void load();
  }, [load, workspaceEpoch]);

  const handleSubmit = async (values: TransactionFormValues) => {
    if (!financeApi) {
      return;
    }
    if (editing) {
      await financeApi.updateTransaction(editing.id, values);
    } else {
      await financeApi.createTransaction(values);
    }
    setShowForm(false);
    setEditing(null);
    await load();
  };

  const handleDelete = async (transaction: Transaction) => {
    if (!financeApi) {
      return;
    }
    if (!window.confirm(`Удалить «${transaction.title}»?`)) {
      return;
    }
    try {
      await financeApi.deleteTransaction(transaction.id);
      await load();
    } catch (err) {
      setError(parseApiError(err, "Не удалось удалить транзакцию"));
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-text">Финансы</h1>
          <p className="mt-1 text-sm text-text-muted">
            Учёт расходов и доходов workspace
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            setEditing(null);
            setShowForm((value) => !value);
          }}
          className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary-hover"
        >
          {showForm && !editing ? "Скрыть форму" : "+ Транзакция"}
        </button>
      </div>
      {error && <ErrorMessage message={error} onDismiss={() => setError("")} />}

      {(showForm || editing) && (
        <TransactionForm
          projects={projects}
          initial={
            editing
              ? {
                  title: editing.title,
                  amount: editing.amount,
                  transaction_type: editing.transaction_type,
                  transaction_date: editing.transaction_date,
                  category: editing.category,
                  notes: editing.notes,
                  project_id: editing.project_id,
                }
              : undefined
          }
          submitLabel={editing ? "Обновить" : "Создать"}
          onSubmit={handleSubmit}
          onCancel={() => {
            setShowForm(false);
            setEditing(null);
          }}
        />
      )}

      {transactions.length === 0 ? (
        <p className="text-sm text-text-muted">Транзакций пока нет</p>
      ) : (
        <ul className="space-y-2">
          {transactions.map((item) => (
            <li
              key={item.id}
              className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border bg-surface px-4 py-3 text-sm"
            >
              <div>
                <p className="font-medium text-text">{item.title}</p>
                <p className="text-xs text-text-muted">
                  {item.transaction_date}
                  {item.category ? ` · ${item.category}` : ""}
                  {item.project_id ? ` · проект #${item.project_id}` : ""}
                </p>
              </div>
              <div className="flex items-center gap-3">
                <span
                  className={
                    item.transaction_type === "expense"
                      ? "font-semibold text-primary"
                      : "font-semibold text-secondary"
                  }
                >
                  {item.transaction_type === "expense" ? "−" : "+"}
                  {item.amount} ₽
                </span>
                <button
                  type="button"
                  className="text-xs text-primary hover:underline"
                  onClick={() => {
                    setEditing(item);
                    setShowForm(true);
                  }}
                >
                  Изменить
                </button>
                <button
                  type="button"
                  className="text-xs text-text-muted hover:underline"
                  onClick={() => void handleDelete(item)}
                >
                  Удалить
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
