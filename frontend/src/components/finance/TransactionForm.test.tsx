import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { TransactionForm } from "./TransactionForm";

describe("TransactionForm", () => {
  it("submits full transaction payload", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(
      <TransactionForm
        projects={[{ id: 7, name: "Alpha" } as never]}
        onSubmit={onSubmit}
      />,
    );

    fireEvent.change(screen.getByLabelText("Название"), {
      target: { value: "Office supplies" },
    });
    fireEvent.change(screen.getByLabelText("Сумма"), {
      target: { value: "150.5" },
    });
    fireEvent.change(screen.getByLabelText("Тип"), {
      target: { value: "income" },
    });
    fireEvent.change(screen.getByLabelText("Категория"), {
      target: { value: "ops" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Сохранить" }));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          title: "Office supplies",
          amount: "150.5",
          transaction_type: "income",
          category: "ops",
        }),
      );
    });
  });

  it("blocks empty title", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<TransactionForm projects={[]} onSubmit={onSubmit} />);
    fireEvent.change(screen.getByLabelText("Сумма"), {
      target: { value: "10" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Сохранить" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Укажите название");
    expect(onSubmit).not.toHaveBeenCalled();
  });
});
