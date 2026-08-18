import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { DeleteProjectButton } from "./DeleteProjectButton";

describe("DeleteProjectButton", () => {
  it("does not delete when confirmation is cancelled", async () => {
    const onConfirmDelete = vi.fn();
    render(
      <DeleteProjectButton
        projectName="Alpha"
        onConfirmDelete={onConfirmDelete}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Удалить" }));
    expect(await screen.findByRole("alertdialog")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Отмена" }));

    await waitFor(() => {
      expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
    });
    expect(onConfirmDelete).not.toHaveBeenCalled();
  });

  it("deletes after confirmation", async () => {
    const onConfirmDelete = vi.fn().mockResolvedValue(undefined);
    render(
      <DeleteProjectButton
        projectName="Alpha"
        onConfirmDelete={onConfirmDelete}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Удалить" }));
    expect(
      await screen.findByText(/будет удалён вместе с WBS/),
    ).toBeInTheDocument();

    const confirmButtons = screen.getAllByRole("button", { name: "Удалить" });
    fireEvent.click(confirmButtons[confirmButtons.length - 1]);

    await waitFor(() => {
      expect(onConfirmDelete).toHaveBeenCalledTimes(1);
    });
  });
});
