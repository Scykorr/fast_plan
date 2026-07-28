import { expect, test } from "@playwright/test";

/**
 * Agent Ops E2E: claim → handoff → meaning approve (UI smoke when feature enabled).
 * Requires Agent Ops enabled for the smoke workspace and E2E credentials.
 */
const email = process.env.E2E_EMAIL || process.env.STAGING_EMAIL || "smoke@fast-plan.ci";
const password =
  process.env.E2E_PASSWORD || process.env.STAGING_PASSWORD || "smokepass123";

async function login(page: import("@playwright/test").Page) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Пароль").fill(password);
  await page.getByRole("button", { name: "Войти" }).click();
  await expect(page).not.toHaveURL(/\/login/, { timeout: 20_000 });
}

test.describe("agent ops", () => {
  test("opens /agent-ops and agents onboarding when enabled", async ({ page }) => {
    test.skip(!email || !password, "E2E_EMAIL/E2E_PASSWORD not set");
    await login(page);
    await page.goto("/agent-ops");
    // Feature may be off — page should still render without crashing
    const heading = page.getByRole("heading", { name: /Agent Ops|мультиагент/i }).first();
    const disabled = page.getByText(/выключ|disabled|не включ/i).first();
    await expect(heading.or(disabled)).toBeVisible({ timeout: 15_000 });

    const agentsTab = page.getByRole("button", { name: /Агенты/i });
    if (await agentsTab.isVisible().catch(() => false)) {
      await agentsTab.click();
      await expect(page.getByText(/Onboarding агента/i)).toBeVisible();
      await expect(
        page.getByRole("button", { name: /service account/i }),
      ).toBeVisible();
    }
  });

  test("claim → handoff → meaning via API helpers when ops enabled", async ({
    request,
    baseURL,
  }) => {
    test.skip(!email || !password, "E2E_EMAIL/E2E_PASSWORD not set");
    const origin = baseURL || "http://127.0.0.1:4173";
    // Prefer API host from env; SPA base may differ
    const apiBase = (process.env.E2E_API_URL || process.env.STAGING_BASE_URL || origin).replace(
      /\/$/,
      "",
    );

    const csrfRes = await request.get(`${apiBase}/api/auth/csrf/`);
    const setCookie = csrfRes.headers()["set-cookie"] || "";
    const csrf =
      /csrftoken=([^;]+)/.exec(Array.isArray(setCookie) ? setCookie.join(";") : setCookie)?.[1] ||
      "";

    const loginRes = await request.post(`${apiBase}/api/auth/login/`, {
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrf,
        Cookie: `csrftoken=${csrf}`,
      },
      data: { email, password },
    });
    test.skip(!loginRes.ok(), `login failed HTTP ${loginRes.status()}`);

    const settings = await request.get(`${apiBase}/api/delivery/settings/`);
    if (!settings.ok()) {
      test.skip(true, "delivery API unavailable");
    }
    const settingsBody = await settings.json();
    if (!settingsBody?.agent_ops_enabled) {
      test.skip(true, "agent_ops_enabled=false — skip claim/handoff flow");
    }

    const overview = await request.get(`${apiBase}/api/delivery/overview/`);
    expect(overview.ok()).toBeTruthy();

    const queue = await request.get(`${apiBase}/api/delivery/queue/`);
    expect(queue.ok()).toBeTruthy();

    // Create a Ready task, claim, handoff, request meaning change, approve
    const create = await request.post(`${apiBase}/api/delivery/tasks/`, {
      data: {
        title: `e2e-claim-${Date.now()}`,
        business_outcome: "e2e",
        context: "e2e",
        scope_in: "claim",
        scope_out: "none",
        ready_criterion: "ok",
        done_criterion: "ok",
        expected_checks: "e2e",
        result_artifact: "pr",
        assignee_role: "backend",
        next_role: "qa",
        canon_url: "https://example.com/c",
        architecture_url: "https://example.com/a",
        planning_doc_url: "https://example.com/p",
        acceptance_url: "https://example.com/acc",
      },
    });
    test.skip(!create.ok(), `create task HTTP ${create.status()}`);
    const task = await create.json();
    const taskId = task.id;

    const claim = await request.post(`${apiBase}/api/delivery/tasks/${taskId}/claim/`, {
      data: {},
    });
    expect(claim.ok()).toBeTruthy();

    const handoff = await request.post(
      `${apiBase}/api/delivery/tasks/${taskId}/handoffs/`,
      {
        data: {
          from_role: "backend",
          to_role: "qa",
          done_summary: "e2e handoff",
          left_summary: "qa next",
          branch_or_pr_url: "https://example.com/pr/1",
          checks_url: "https://example.com/checks",
          open_questions: "none",
        },
      },
    );
    expect(handoff.ok()).toBeTruthy();

    const meaning = await request.patch(`${apiBase}/api/delivery/tasks/${taskId}/`, {
      data: {
        business_outcome: "e2e meaning updated",
      },
    });
    // Agent meaning may queue for approval rather than apply directly
    expect([200, 202].includes(meaning.status()) || meaning.ok()).toBeTruthy();
    const meaningBody = await meaning.json().catch(() => ({}));
    const reqId = meaningBody.meaning_change_request_id;
    if (reqId) {
      const approve = await request.post(
        `${apiBase}/api/delivery/tasks/${taskId}/meaning-changes/${reqId}/review/`,
        { data: { decision: "approve" } },
      );
      expect(approve.ok()).toBeTruthy();
    }
  });
});
