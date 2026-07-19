import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { AppLayout } from "./AppLayout";
import { AuthProvider } from "../context/AuthContext";
import { WorkspaceProvider } from "../context/WorkspaceContext";

function renderLayout() {
  return render(
    <MemoryRouter>
      <AuthProvider>
        <WorkspaceProvider>
          <Routes>
            <Route element={<AppLayout />}>
              <Route index element={<div>Home</div>} />
            </Route>
          </Routes>
        </WorkspaceProvider>
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("AppLayout", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 401,
        json: async () => ({}),
      }),
    );
  });

  it("shows mobile menu button on small screens", () => {
    renderLayout();
    expect(screen.getByLabelText("Открыть меню")).toBeInTheDocument();
  });

  it("opens mobile drawer when menu clicked", async () => {
    const user = userEvent.setup();
    renderLayout();
    await user.click(screen.getByLabelText("Открыть меню"));
    expect(screen.getByLabelText("Закрыть меню")).toBeInTheDocument();
  });
});
