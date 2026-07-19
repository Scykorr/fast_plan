import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { InviteMemberForm } from "./InviteMemberForm";

describe("InviteMemberForm", () => {
  it("submits email and role", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<InviteMemberForm onSubmit={onSubmit} />);

    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "Editor@Example.com" },
    });
    fireEvent.change(screen.getByLabelText("Роль"), {
      target: { value: "viewer" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Пригласить" }));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith("editor@example.com", "viewer");
    });
  });

  it("blocks empty email", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<InviteMemberForm onSubmit={onSubmit} />);
    const form = screen.getByRole("button", { name: "Пригласить" }).closest("form");
    fireEvent.submit(form!);
    expect(await screen.findByRole("alert")).toHaveTextContent("Укажите email");
    expect(onSubmit).not.toHaveBeenCalled();
  });
});
