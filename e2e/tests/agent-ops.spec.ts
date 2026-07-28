import { expect, test } from "@playwright/test";

/**
 * Agent Ops UI smoke. Full claim→handoff→meaning is covered by backend pytest
 * (test_delivery_p9). Optional deep API flow: set E2E_AGENT_OPS=1.
 */
const email = process.env.E2E_EMAIL || process.env.STAGING_EMAIL || "smoke@fast-plan.ci";
const password =
  process.env.E2E_PASSWORD || process.env.STAGING_PASSWORD || "smokepass123";
const workspaceId =
  process.env.E2E_WORKSPACE_ID || process.env.STAGING_WORKSPACE_ID || "";

test.describe("agent ops", () => {
  test("opens /agent-ops with heading and toggle", async ({ page }) => {
    test.skip(!email || !password, "E2E_EMAIL/E2E_PASSWORD not set");

    await page.goto("/login");
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Пароль").fill(password);
    await page.getByRole("button", { name: "Войти" }).click();
    await expect(page).not.toHaveURL(/\/login/, { timeout: 20_000 });

    await page.goto("/agent-ops");
    await expect(page.getByRole("heading", { name: "Agent Ops" })).toBeVisible({
      timeout: 15_000,
    });
    await expect(
      page.getByRole("button", { name: /Включить Agent Ops|Выключить/i }),
    ).toBeVisible();

    // When enabled, agents tab shows onboarding copy.
    const enableBtn = page.getByRole("button", { name: "Включить Agent Ops" });
    if (await enableBtn.isVisible().catch(() => false)) {
      await enableBtn.click();
      await expect(page.getByRole("button", { name: "Выключить" })).toBeVisible({
        timeout: 10_000,
      });
    }
    const agentsTab = page.getByRole("button", { name: "Агенты" });
    if (await agentsTab.isVisible().catch(() => false)) {
      await agentsTab.click();
      await expect(page.getByText("Onboarding агента")).toBeVisible();
    }
  });

  test("claim → handoff → meaning via API when E2E_AGENT_OPS=1", async ({
    page,
  }) => {
    test.skip(process.env.E2E_AGENT_OPS !== "1", "set E2E_AGENT_OPS=1 to run");
    test.skip(!email || !password || !workspaceId, "credentials/workspace required");

    await page.goto("/login");
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Пароль").fill(password);
    await page.getByRole("button", { name: "Войти" }).click();
    await expect(page).not.toHaveURL(/\/login/, { timeout: 20_000 });

    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      "X-Workspace-Id": workspaceId,
    };
    const csrf = await page.request.get("/api/auth/csrf/");
    const csrfJson = await csrf.json();
    if (csrfJson?.csrfToken) {
      headers["X-CSRFToken"] = csrfJson.csrfToken as string;
    }

    await page.request.patch("/api/delivery/settings/", {
      headers,
      data: { agent_ops_enabled: true },
    });

    const create = await page.request.post("/api/delivery/tasks/", {
      headers,
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
    expect(create.ok(), `create HTTP ${create.status()}`).toBeTruthy();
    const task = await create.json();

    const claim = await page.request.post(`/api/delivery/tasks/${task.id}/claim/`, {
      headers,
      data: {},
    });
    expect(claim.ok(), `claim HTTP ${claim.status()}`).toBeTruthy();

    const handoff = await page.request.post(
      `/api/delivery/tasks/${task.id}/handoffs/`,
      {
        headers,
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
    expect(handoff.ok(), `handoff HTTP ${handoff.status()}`).toBeTruthy();

    const meaning = await page.request.patch(`/api/delivery/tasks/${task.id}/`, {
      headers,
      data: { business_outcome: "e2e meaning updated", title: "e2e meaning title" },
    });
    expect(meaning.ok(), `meaning HTTP ${meaning.status()}`).toBeTruthy();
    const meaningBody = await meaning.json();
    const reqId = meaningBody.meaning_change_request_id;
    if (reqId) {
      const approve = await page.request.post(
        `/api/delivery/tasks/${task.id}/meaning-changes/${reqId}/review/`,
        { headers, data: { decision: "approve" } },
      );
      expect(approve.ok(), `approve HTTP ${approve.status()}`).toBeTruthy();
    }
  });
});
