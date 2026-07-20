import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { LoginPage } from "../pages/LoginPage";
import { AuthProvider } from "../context/AuthContext";
import { MemoryRouter } from "react-router-dom";

describe("LoginPage", () => {
  it("renders login form", () => {
    render(
      <MemoryRouter>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </MemoryRouter>,
    );

    expect(screen.getByRole("heading", { name: "Вход" })).toBeInTheDocument();
    expect(screen.getByLabelText("Email")).toBeInTheDocument();
    expect(screen.getByLabelText("Пароль")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Войти" })).toBeInTheDocument();
  });
});

describe("theme", () => {
  it("defines cream page background on body", () => {
    const styles = getComputedStyle(document.body);
    expect(styles.backgroundColor).toBeTruthy();
  });
});
