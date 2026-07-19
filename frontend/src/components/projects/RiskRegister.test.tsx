import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { RiskRegister } from "./RiskRegister";

describe("RiskRegister", () => {
  it("submits risk with probability and impact", async () => {
    const onAdd = vi.fn().mockResolvedValue(undefined);
    render(<RiskRegister risks={[]} onAdd={onAdd} onDelete={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: "+ Риск" }));
    fireEvent.change(screen.getByLabelText("Название"), {
      target: { value: "Scope creep" },
    });
    fireEvent.change(screen.getByLabelText("Вероятность"), {
      target: { value: "4" },
    });
    fireEvent.change(screen.getByLabelText("Влияние"), {
      target: { value: "5" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Добавить" }));

    await waitFor(() => {
      expect(onAdd).toHaveBeenCalledWith({
        title: "Scope creep",
        probability: 4,
        impact: 5,
      });
    });
  });

  it("blocks empty title", async () => {
    const onAdd = vi.fn().mockResolvedValue(undefined);
    render(<RiskRegister risks={[]} onAdd={onAdd} onDelete={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "+ Риск" }));
    fireEvent.click(screen.getByRole("button", { name: "Добавить" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Укажите название риска",
    );
    expect(onAdd).not.toHaveBeenCalled();
  });
});
