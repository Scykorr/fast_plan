import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { AppLayout } from "./AppLayout";
import { AuthProvider } from "../context/AuthContext";
import { LocaleProvider } from "../context/LocaleContext";
import { ThemeProvider } from "../context/ThemeContext";
import { WorkspaceProvider } from "../context/WorkspaceContext";

function renderLayout(initialPath = "/") {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <ThemeProvider>
        <LocaleProvider>
          <AuthProvider>
            <WorkspaceProvider>
              <Routes>
                <Route element={<AppLayout />}>
                  <Route index element={<div>Home</div>} />
                  <Route path="clients" element={<div>Clients</div>} />
                  <Route path="projects" element={<div>Projects</div>} />
                </Route>
              </Routes>
            </WorkspaceProvider>
          </AuthProvider>
        </LocaleProvider>
      </ThemeProvider>
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

  it("groups nav items and expands the active section", () => {
    renderLayout("/clients");
    expect(screen.getAllByRole("button", { name: /CRM/i }).length).toBeGreaterThan(0);
    expect(screen.getAllByText("Клиенты").length).toBeGreaterThan(0);
    expect(screen.queryByText("Мои задачи")).not.toBeInTheDocument();
  });

  it("expands a collapsed group on click", async () => {
    const user = userEvent.setup();
    renderLayout("/");
    expect(screen.queryByText("Клиенты")).not.toBeInTheDocument();
    for (const button of screen.getAllByRole("button", { name: /CRM/i })) {
      await user.click(button);
    }
    expect(screen.getAllByText("Клиенты").length).toBeGreaterThan(0);
  });
});
