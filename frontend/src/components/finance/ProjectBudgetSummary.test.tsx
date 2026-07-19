import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ProjectBudgetSummary } from "./ProjectBudgetSummary";

describe("ProjectBudgetSummary", () => {
  it("renders budget, expenses, income and balance", () => {
    render(
      <ProjectBudgetSummary
        finance={{
          project_id: 1,
          budget: 100000,
          actual_expenses: 25000,
          actual_income: 5000,
          balance: 80000,
          transactions: [],
        }}
      />,
    );

    expect(screen.getByText("Бюджет")).toBeInTheDocument();
    expect(screen.getByText("100 000 \u20BD")).toBeInTheDocument();
    expect(screen.getByText("25 000 \u20BD")).toBeInTheDocument();
    expect(screen.getByText("5 000 \u20BD")).toBeInTheDocument();
    expect(screen.getByText("80 000 \u20BD")).toBeInTheDocument();
    expect(screen.getByText("25%")).toBeInTheDocument();
  });
});
