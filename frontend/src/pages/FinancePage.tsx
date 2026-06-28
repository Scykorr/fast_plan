import { useCallback, useEffect, useState } from "react";

import { parseApiError } from "../api/errors";
import type { Transaction } from "../api/finance";
import { ErrorMessage } from "../components/ErrorMessage";
import { useFinanceApi } from "../hooks/useFinanceApi";

export function FinancePage() {
  const financeApi = useFinanceApi();
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    if (!financeApi) {
      return;
    }
    try {
      setTransactions(await financeApi.getTransactions());
    } catch (err) {
      setError(parseApiError(err, "Не удалось загрузить транзакции"));
    }
  }, [financeApi]);

  useEffect(() => {
    void load();
  }, [load]);

  const handleAdd = async () => {
    if (!financeApi) {
      return;
    }
    const title = window.prompt("Название транзакции");
    const amount = window.prompt("Сумма");
    if (!title?.trim() || !amount) {
      return;
    }
    try {
      await financeApi.createTransaction({
        title: title.trim(),
        amount,
        transaction_type: "expense",
        transaction_date: new Date().toISOString().slice(0, 10),
      });
      await load();
    } catch (err) {
      setError(parseApiError(err, "Не удалось создать транзакцию"));
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
          onClick={() => void handleAdd()}
          className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary-hover"
        >
          + Транзакция
        </button>
      </div>
      {error && <ErrorMessage message={error} onDismiss={() => setError("")} />}
      {transactions.length === 0 ? (
        <p className="text-sm text-text-muted">Транзакций пока нет</p>
      ) : (
        <ul className="space-y-2">
          {transactions.map((item) => (
            <li
              key={item.id}
              className="flex items-center justify-between rounded-lg border border-border bg-surface px-4 py-3 text-sm"
            >
              <div>
                <p className="font-medium text-text">{item.title}</p>
                <p className="text-xs text-text-muted">
                  {item.transaction_date}
                  {item.project_id ? ` · проект #${item.project_id}` : ""}
                </p>
              </div>
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
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
