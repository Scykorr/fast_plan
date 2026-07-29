#!/usr/bin/env node
/**
 * Automated smoke checks for staging / local Fast Plan deployments.
 *
 * Usage:
 *   node scripts/staging-smoke-check.mjs
 *   node scripts/staging-smoke-check.mjs --offline
 *
 * Environment:
 *   STAGING_BASE_URL       API base (default http://127.0.0.1:8000)
 *   STAGING_FRONTEND_URL   SPA URL for PWA checks (optional)
 *   STAGING_EMAIL          Login email for authenticated smoke (optional)
 *   STAGING_PASSWORD       Login password (optional)
 *   STAGING_SHARE_TOKEN    Guest share token for /api/share/ check (optional)
 *   STAGING_PROJECT_ID     Project id for WBS refine API smoke (optional)
 *   STAGING_EXPECT_MICROSOFT_SSO  Set to 1 to require microsoft:true on providers
 */

import { readFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const rootDir = join(dirname(fileURLToPath(import.meta.url)), "..");
const offline = process.argv.includes("--offline");

const BASE_URL = (process.env.STAGING_BASE_URL || "http://127.0.0.1:8000").replace(
  /\/$/,
  "",
);
const FRONTEND_URL = process.env.STAGING_FRONTEND_URL?.replace(/\/$/, "");
const EMAIL = process.env.STAGING_EMAIL;
const PASSWORD = process.env.STAGING_PASSWORD;
const SHARE_TOKEN = process.env.STAGING_SHARE_TOKEN;
const PROJECT_ID = process.env.STAGING_PROJECT_ID;
const WORKSPACE_ID = process.env.STAGING_WORKSPACE_ID;

const results = [];

function readExpectedVersion() {
  return readFileSync(join(rootDir, "VERSION"), "utf8").trim();
}

function pass(name, detail = "") {
  results.push({ name, ok: true, detail });
  console.log(`✓ ${name}${detail ? `: ${detail}` : ""}`);
}

function fail(name, detail = "") {
  results.push({ name, ok: false, detail });
  console.error(`✗ ${name}${detail ? `: ${detail}` : ""}`);
}

function warn(name, detail = "") {
  results.push({ name, ok: true, warn: true, detail });
  console.warn(`⚠ ${name}${detail ? `: ${detail}` : ""}`);
}

function parseSetCookie(setCookieHeader) {
  if (!setCookieHeader) {
    return "";
  }
  const parts = Array.isArray(setCookieHeader) ? setCookieHeader : [setCookieHeader];
  return parts.map((part) => part.split(";")[0]).join("; ");
}

function cookieValue(cookieHeader, name) {
  for (const part of cookieHeader.split(";")) {
    const trimmed = part.trim();
    if (!trimmed) continue;
    const index = trimmed.indexOf("=");
    if (index <= 0) continue;
    if (trimmed.slice(0, index) === name) {
      return trimmed.slice(index + 1);
    }
  }
  return "";
}

function mergeCookies(existing, setCookieHeader) {
  const jar = new Map(
    existing
      .split(";")
      .map((pair) => pair.trim())
      .filter(Boolean)
      .map((pair) => {
        const index = pair.indexOf("=");
        return [pair.slice(0, index), pair.slice(index + 1)];
      }),
  );
  const incoming = parseSetCookie(setCookieHeader);
  for (const pair of incoming.split(";").filter(Boolean)) {
    const index = pair.indexOf("=");
    jar.set(pair.slice(0, index).trim(), pair.slice(index + 1).trim());
  }
  return Array.from(jar.entries())
    .map(([key, value]) => `${key}=${value}`)
    .join("; ");
}

async function fetchJson(path, options = {}) {
  const url = `${BASE_URL}${path}`;
  const response = await fetch(url, options);
  let body = null;
  try {
    body = await response.json();
  } catch {
    body = null;
  }
  return { response, body };
}

function runVersionSync() {
  const proc = spawnSync(process.execPath, ["scripts/check-version-sync.mjs"], {
    cwd: rootDir,
    encoding: "utf8",
  });
  if (proc.status === 0) {
    pass("version sync", proc.stdout.trim());
    return true;
  }
  fail("version sync", proc.stderr.trim() || proc.stdout.trim());
  return false;
}

async function checkHealth() {
  const expected = readExpectedVersion();
  const { response, body } = await fetchJson("/api/health/");
  if (!response.ok || body?.status !== "ok") {
    fail("health", `HTTP ${response.status}`);
    return false;
  }
  if (body.version !== expected) {
    fail("health version", `expected ${expected}, got ${body.version}`);
    return false;
  }
  pass("health", `version ${body.version}`);
  return true;
}

async function checkExtendedHealth() {
  const { response, body } = await fetchJson("/api/health/?extended=1");
  if (!response.ok || !body?.checks) {
    fail("extended health", `HTTP ${response.status}`);
    return false;
  }
  const checks = body.checks;
  if (checks.database === "ok") {
    pass("extended health database", checks.database);
  } else {
    fail("extended health database", String(checks.database));
  }
  if (checks.redis === "ok") {
    pass("extended health redis", checks.redis);
  } else if (checks.redis === "skipped") {
    warn("extended health redis", "skipped (locmem — not for production staging)");
  } else {
    fail("extended health redis", String(checks.redis));
  }
  if (checks.celery_eager === true) {
    warn("celery eager", "CELERY_TASK_ALWAYS_EAGER=true — tasks run in-process");
  } else {
    pass("celery eager", "false");
  }
  if (String(checks.email_backend).includes("console")) {
    warn("email backend", "console backend — SMTP not configured");
  } else {
    pass("email backend", checks.email_backend);
  }
  return checks.database === "ok";
}

async function checkFrontendPwa() {
  if (!FRONTEND_URL) {
    warn("frontend PWA", "STAGING_FRONTEND_URL not set — skipped");
    return true;
  }
  const manifestUrl = `${FRONTEND_URL}/manifest.webmanifest`;
  const response = await fetch(manifestUrl);
  if (!response.ok) {
    fail("frontend manifest", `HTTP ${response.status} at ${manifestUrl}`);
    return false;
  }
  const manifest = await response.json();
  if (!manifest.name || !manifest.theme_color) {
    fail("frontend manifest fields", "missing name or theme_color");
    return false;
  }
  pass("frontend manifest", manifest.short_name || manifest.name);
  const shell = await fetch(FRONTEND_URL);
  if (!shell.ok) {
    fail("frontend shell", `HTTP ${shell.status}`);
    return false;
  }
  const html = await shell.text();
  if (!html.includes('id="root"')) {
    fail("frontend shell", "missing #root mount point");
    return false;
  }
  pass("frontend shell", FRONTEND_URL);
  return true;
}

async function checkAuthSmoke() {
  if (!EMAIL || !PASSWORD) {
    warn("auth smoke", "STAGING_EMAIL/PASSWORD not set — skipped");
    return true;
  }
  let cookies = "";
  const login = await fetchJson("/api/auth/login/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: EMAIL, password: PASSWORD }),
  });
  cookies = mergeCookies(cookies, login.response.headers.getSetCookie?.() ?? []);
  if (!login.response.ok) {
    fail("auth login", `HTTP ${login.response.status}`);
    return false;
  }
  pass("auth login", EMAIL);

  const csrf = await fetchJson("/api/auth/csrf/", { headers: { Cookie: cookies } });
  cookies = mergeCookies(cookies, csrf.response.headers.getSetCookie?.() ?? []);
  const csrfToken =
    csrf.body?.csrfToken || cookieValue(cookies, "csrftoken") || "";

  const headers = {
    Cookie: cookies,
    ...(WORKSPACE_ID ? { "X-Workspace-Id": String(WORKSPACE_ID) } : {}),
  };
  const projects = await fetchJson("/api/projects/", { headers });
  if (!projects.response.ok) {
    fail("auth projects list", `HTTP ${projects.response.status}`);
    return false;
  }
  pass(
    "auth projects list",
    `${Array.isArray(projects.body) ? projects.body.length : 0} projects`,
  );

  if (PROJECT_ID) {
    const draft = await fetchJson(`/api/projects/${PROJECT_ID}/ai-draft/`, {
      method: "POST",
      headers: {
        ...headers,
        "Content-Type": "application/json",
        ...(csrfToken ? { "X-CSRFToken": csrfToken } : {}),
      },
      body: JSON.stringify({ target: "wbs" }),
    });
    cookies = mergeCookies(cookies, draft.response.headers.getSetCookie?.() ?? []);
    if (!draft.response.ok || draft.body?.target !== "wbs") {
      fail("ai wbs draft", `HTTP ${draft.response.status}`);
      return false;
    }
    const refine = await fetchJson(`/api/projects/${PROJECT_ID}/ai-draft/`, {
      method: "POST",
      headers: {
        ...headers,
        Cookie: cookies,
        "Content-Type": "application/json",
        ...(csrfToken ? { "X-CSRFToken": csrfToken } : {}),
      },
      body: JSON.stringify({
        target: "wbs",
        refinement: "добавь этап тестирования",
        current_draft: {
          nodes: draft.body.nodes,
          dependencies: draft.body.dependencies ?? [],
        },
      }),
    });
    if (!refine.response.ok || refine.body?.target !== "wbs") {
      fail("ai wbs refine", `HTTP ${refine.response.status}`);
      return false;
    }
    if ((refine.body.nodes?.length ?? 0) <= (draft.body.nodes?.length ?? 0)) {
      fail("ai wbs refine", "expected more nodes after refinement");
      return false;
    }
    pass("ai wbs refine", `${draft.body.nodes.length} → ${refine.body.nodes.length} nodes`);
  } else {
    warn("ai wbs refine", "STAGING_PROJECT_ID not set — skipped");
  }

  // P8 process + CRM calendar smoke (authenticated)
  const processGets = [
    { path: "/api/process/metrics/", name: "process metrics", ok: (b) => typeof b?.instance_count === "number" },
    { path: "/api/process/mining/", name: "process mining", ok: (b) => Array.isArray(b?.dfg) },
    { path: "/api/process/decisions/", name: "process decisions", ok: (b) => Array.isArray(b) },
    { path: "/api/process/cases/", name: "process cases", ok: (b) => Array.isArray(b) },
    {
      path: "/api/process/cases/definitions/",
      name: "process case defs",
      ok: (b) => Array.isArray(b),
    },
    { path: "/api/process/packs/", name: "process packs", ok: (b) => Array.isArray(b) },
    {
      path: "/api/calendar/crm/?year=2026&month=7",
      name: "crm calendar events",
      ok: (b) => Array.isArray(b),
    },
    {
      path: "/api/crm/calendar/providers/",
      name: "crm calendar providers",
      ok: (b) =>
        typeof b?.microsoft === "boolean" && typeof b?.google === "boolean",
    },
    {
      path: "/api/crm/calendar/connections/",
      name: "crm calendar connections",
      ok: (b) => Array.isArray(b),
    },
    {
      path: "/api/crm/calendar/conflicts/",
      name: "crm calendar conflicts",
      ok: (b) => Array.isArray(b),
    },
    {
      path: "/api/crm/connectors/catalog/",
      name: "crm connectors catalog",
      ok: (b) =>
        Array.isArray(b?.providers) &&
        b.providers.some((row) => row?.provider === "telephony"),
    },
    {
      path: "/api/crm/saved-filters/",
      name: "crm saved filters",
      ok: (b) => Array.isArray(b),
    },
            {
              path: "/api/crm/custom-fields/",
              name: "crm custom fields",
              ok: (b) => Array.isArray(b),
            },
            {
              path: "/api/crm/skus/",
              name: "crm skus",
              ok: (b) => Array.isArray(b),
            },
          ];
  for (const check of processGets) {
    const res = await fetchJson(check.path, { headers });
    if (!res.response.ok || !check.ok(res.body)) {
      fail(check.name, `HTTP ${res.response.status}`);
      return false;
    }
    pass(check.name);
  }

  // CRM custom fields write smoke (definition round-trip)
  const mutHeaders = {
    ...headers,
    "Content-Type": "application/json",
    ...(csrfToken ? { "X-CSRFToken": csrfToken } : {}),
  };
  const cfKey = `smoke_cf_${Date.now().toString(36)}`;
  const cfCreate = await fetchJson("/api/crm/custom-fields/", {
    method: "POST",
    headers: mutHeaders,
    body: JSON.stringify({
      target: "deal",
      key: cfKey,
      label: "Smoke CF",
      field_type: "text",
    }),
  });
  if (!cfCreate.response.ok || !cfCreate.body?.id) {
    fail("crm custom fields create", `HTTP ${cfCreate.response.status}`);
    return false;
  }
  pass("crm custom fields create", cfKey);
  const cfList = await fetchJson("/api/crm/custom-fields/?target=deal&active=0", {
    headers,
  });
  if (
    !cfList.response.ok ||
    !Array.isArray(cfList.body) ||
    !cfList.body.some((row) => row?.key === cfKey)
  ) {
    fail("crm custom fields list", "created key not found");
    return false;
  }
  pass("crm custom fields list", "includes created key");

  // Agent Ops delivery smoke — enable if needed, then hit overview/queue/agents
  let deliverySettings = await fetchJson("/api/delivery/settings/", { headers });
  if (!deliverySettings.response.ok) {
    fail("delivery settings", `HTTP ${deliverySettings.response.status}`);
    return false;
  }
  if (!deliverySettings.body?.agent_ops_enabled) {
    const enable = await fetchJson("/api/delivery/settings/", {
      method: "PATCH",
      headers: mutHeaders,
      body: JSON.stringify({ agent_ops_enabled: true }),
    });
    if (!enable.response.ok || !enable.body?.agent_ops_enabled) {
      fail("delivery enable agent ops", `HTTP ${enable.response.status}`);
      return false;
    }
    pass("delivery enable agent ops");
    deliverySettings = enable;
  } else {
    pass("delivery settings", "agent_ops_enabled");
  }
  for (const path of [
    "/api/delivery/overview/",
    "/api/delivery/queue/",
    "/api/delivery/agents/",
  ]) {
    const res = await fetchJson(path, { headers });
    if (!res.response.ok) {
      fail(`delivery ${path}`, `HTTP ${res.response.status}`);
      return false;
    }
    pass(`delivery ${path}`);
  }

  return true;
}

async function checkSsoProviders() {
  const { response, body } = await fetchJson("/api/auth/oauth/providers/");
  if (!response.ok || typeof body?.microsoft !== "boolean" || typeof body?.google !== "boolean") {
    fail("oauth providers", `HTTP ${response.status}`);
    return false;
  }
  if (body.google === true) {
    warn("oauth google", "unexpectedly enabled (DISABLED_PROVIDERS should hide Google)");
  } else {
    pass("oauth google", "disabled");
  }
  const expectMs = process.env.STAGING_EXPECT_MICROSOFT_SSO === "1";
  if (body.microsoft) {
    pass("oauth microsoft", "configured");
    const start = await fetch(`${BASE_URL}/api/auth/oauth/microsoft/`, {
      redirect: "manual",
    });
    const loc = start.headers.get("location") || "";
    if ([302, 301, 303, 307, 308].includes(start.status) && loc.includes("microsoftonline.com")) {
      pass("oauth microsoft start", "redirects to IdP");
    } else if (start.status === 400) {
      fail("oauth microsoft start", "provider listed but start returned 400");
      return false;
    } else {
      warn("oauth microsoft start", `HTTP ${start.status}`);
    }
  } else if (expectMs) {
    fail("oauth microsoft", "STAGING_EXPECT_MICROSOFT_SSO=1 but microsoft=false");
    return false;
  } else {
    warn("oauth microsoft", "not configured — set OAUTH_MICROSOFT_* to enable");
  }
  return true;
}

async function checkPublicShare() {
  if (!SHARE_TOKEN) {
    warn("guest share", "STAGING_SHARE_TOKEN not set — skipped");
    return true;
  }
  const { response, body } = await fetchJson(`/api/share/${SHARE_TOKEN}/`);
  if (!response.ok || !body?.share) {
    fail("guest share", `HTTP ${response.status}`);
    return false;
  }
  pass("guest share", body.share.project_name || SHARE_TOKEN);
  return true;
}

async function main() {
  console.log(`Fast Plan staging smoke-check${offline ? " (offline)" : ""}\n`);

  runVersionSync();
  if (offline) {
    summarize();
    return;
  }

  console.log(`\nTarget API: ${BASE_URL}\n`);

  try {
    await checkHealth();
    await checkExtendedHealth();
    await checkFrontendPwa();
    await checkSsoProviders();
    await checkAuthSmoke();
    await checkPublicShare();
  } catch (error) {
    fail("network", error instanceof Error ? error.message : String(error));
  }

  summarize();
}

function summarize() {
  const hardFails = results.filter((item) => !item.ok);
  const warnings = results.filter((item) => item.warn);
  console.log(`\n${results.length - hardFails.length}/${results.length} checks passed`);
  if (warnings.length > 0) {
    console.log(`${warnings.length} warning(s)`);
  }
  if (hardFails.length > 0) {
    process.exit(1);
  }
}

main();
