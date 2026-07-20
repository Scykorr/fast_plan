import { expect, test } from "@playwright/test";

const email = process.env.E2E_EMAIL || process.env.STAGING_EMAIL || "smoke@fast-plan.ci";
const password =
  process.env.E2E_PASSWORD || process.env.STAGING_PASSWORD || "smokepass123";

test.describe("login", () => {
  test("shows login form", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByRole("heading", { name: "Вход" })).toBeVisible();
    await expect(page.getByLabel("Email")).toBeVisible();
    await expect(page.getByLabel("Пароль")).toBeVisible();
    await expect(page.getByRole("button", { name: "Войти" })).toBeVisible();
  });

  test("logs in with smoke fixtures", async ({ page }) => {
    test.skip(!email || !password, "E2E_EMAIL/E2E_PASSWORD not set");

    await page.goto("/login");
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Пароль").fill(password);
    await page.getByRole("button", { name: "Войти" }).click();

    await expect(page).not.toHaveURL(/\/login/, { timeout: 20_000 });
    await expect(page.getByText("Fast Plan").first()).toBeVisible();
    await expect(page.getByText("Дашборд").or(page.getByText("Dashboard"))).toBeVisible({
      timeout: 15_000,
    });
  });
});
