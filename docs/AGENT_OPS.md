# Agent Ops — onboarding & runbook

Operational guide for Fast Plan multi-agent delivery (`/agent-ops`, `/api/delivery/`).

## Enable

1. Open **Agent Ops** in the UI.
2. Click **Включить Agent Ops** (`PATCH /api/delivery/settings/` → `agent_ops_enabled: true`).
3. Optional: set **GitHub webhook secret** and **PAT** on the same page (HMAC + attach-PR).

## Provision an agent

UI: tab **Агенты** → choose role → **Создать service account + token**.

API:

```http
POST /api/delivery/agents/service-accounts/
Authorization: Token <owner-or-editor-token>
X-Workspace-Id: <id>
Content-Type: application/json

{ "role": "backend" }
```

Response includes a one-time API token. Store it in the agent secret store.

## Auth for agents

```http
Authorization: Token <agent-token>
X-Workspace-Id: <workspace-id>
Content-Type: application/json
Idempotency-Key: <optional-uuid>   # for claim / status mutations
```

## Typical cycle

1. **Мои задачи** — `GET /api/delivery/my-tasks/` (новые / в работе / ждут ответа / возврат)
2. **Queue** — `GET /api/delivery/queue/?role=backend&status=ready`
3. **Claim** — `POST /api/delivery/tasks/{id}/claim/`
4. **Work** — PATCH task fields; journal `POST .../comments/` `{ "kind": "result", "body": "..." }`
5. **Handoff** — `POST /api/delivery/tasks/{id}/handoffs/` with `to_role`, optional `to_user`, `reason`, `expected_next_step`, `done_summary`
5. **Meaning changes** — agents cannot silently rewrite title/outcome; Owner/Planner approve via  
   `POST /api/delivery/tasks/{id}/meaning-changes/{req_id}/review/` `{ "decision": "approve" }`
6. **Ready-gate** — required doc URLs must be set before Ready / claim rules apply

## Roles (defaults)

`owner` · `planner` · `backend` · `frontend` · `qa` · `devops` · `reviewer` — see effective_actions on agent profile and field ACL matrix in `delivery/services.py`.

## CI / E2E

- Unit/API: `backend/tests/test_delivery_p9.py`
- Playwright UI smoke always; deep claim→handoff→meaning when `E2E_AGENT_OPS=1`  
  (`e2e/tests/agent-ops.spec.ts`, enabled in GitHub Actions e2e job)
- Staging smoke hits `/api/delivery/settings|overview|queue|agents/` when ops enabled

## Webhooks

`POST /api/delivery/webhooks/github/` — HMAC `X-Hub-Signature-256` with workspace webhook secret.  
Events: pull_request, check_run / check_suite status updates on linked PRs.
