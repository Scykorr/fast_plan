import { request, requestBlob } from "./client";

export type Transaction = {
  id: number;
  project_id: number | null;
  title: string;
  amount: string;
  transaction_type: "expense" | "income";
  category: string;
  transaction_date: string;
  notes: string;
  created_at: string;
};

export type ProjectFinance = {
  project_id: number;
  budget: number;
  actual_expenses: number;
  actual_income: number;
  balance: number;
  transactions: Transaction[];
};

export function createFinanceApi() {
  return {
    getTransactions: (projectId?: number) =>
      request<Transaction[]>(
        projectId
          ? `/finance/transactions/?project_id=${projectId}`
          : "/finance/transactions/",
        {}
      ),

    createTransaction: (body: {
      project_id?: number | null;
      title: string;
      amount: string;
      transaction_type?: string;
      category?: string;
      transaction_date: string;
      notes?: string;
    }) =>
      request<Transaction>(
        "/finance/transactions/",
        {
          method: "POST",
          body: JSON.stringify(body),
        }
      ),

    updateTransaction: (
      id: number,
      body: {
        project_id?: number | null;
        title?: string;
        amount?: string;
        transaction_type?: string;
        category?: string;
        transaction_date?: string;
        notes?: string;
      },
    ) =>
      request<Transaction>(
        `/finance/transactions/${id}/`,
        {
          method: "PATCH",
          body: JSON.stringify(body),
        }
      ),

    deleteTransaction: (id: number) =>
      request<void>(`/finance/transactions/${id}/`, { method: "DELETE" }),

    getProjectFinance: (projectId: number) =>
      request<ProjectFinance>(`/projects/${projectId}/finance/`, {}),

    exportTransactions: (format: "csv" | "xlsx", projectId?: number) => {
      const query = new URLSearchParams({ format });
      if (projectId) {
        query.set("project_id", String(projectId));
      }
      return requestBlob(`/finance/transactions/export/?${query.toString()}`);
    },
  };
}
