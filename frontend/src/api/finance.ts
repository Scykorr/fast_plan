import { request } from "./client";

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

export function createFinanceApi(token: string) {
  return {
    getTransactions: (projectId?: number) =>
      request<Transaction[]>(
        projectId
          ? `/finance/transactions/?project_id=${projectId}`
          : "/finance/transactions/",
        {},
        token,
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
      request<Transaction>("/finance/transactions/", {
        method: "POST",
        body: JSON.stringify(body),
      }, token),

    getProjectFinance: (projectId: number) =>
      request<ProjectFinance>(`/projects/${projectId}/finance/`, {}, token),
  };
}
