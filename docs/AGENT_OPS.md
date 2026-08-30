# Agent Ops — onboarding & runbook

Operational guide for Fast Plan multi-agent delivery (`/agent-ops`, `/api/delivery/`).

## Enable

Agent Ops is **on by default** for every workspace (`agent_ops_enabled=true`). To disable: Agent Ops UI → **Выключить**, or `PATCH /api/delivery/settings/` with `{ "agent_ops_enabled": false }`. Env: `AGENT_OPS_ENABLED_DEFAULT=false` affects **new** `DeliverySettings` rows only.

Optional GitHub: set **webhook secret** and **PAT** on the same page (HMAC + attach-PR).

## Provision an agent

UI: tab **Агенты** → choose role (optional **Имя**) → **Создать service account + token**.
Rename later via **Переименовать** on the agent card, or:

```http
PATCH /api/delivery/agents/{id}/
{ "display_name": "Backend Agent" }
```

Один агент / один чат Cursor (или Codex) = **одна** учётка + **свой** токен. Несколько чатов → несколько service accounts (backend, frontend, qa, …). Как это стыкуется с формулировкой заказчика: [CUSTOMER_AGENT_LOOP.md](CUSTOMER_AGENT_LOOP.md) §8.3.

API:

```http
POST /api/delivery/agents/service-accounts/
Authorization: Token <owner-or-editor-token>
X-Workspace-Id: <id>
Content-Type: application/json

{ "role": "backend" }
```

Response includes a one-time API token. Store it in the agent secret store (per chat / per agent — never shared).

## Auth for agents

```http
Authorization: Token <agent-token>
X-Workspace-Id: <workspace-id>
Content-Type: application/json
Idempotency-Key: <optional-uuid>   # for claim / status mutations
```

## Typical cycle

1. **Мои задачи** — `GET /api/delivery/my-tasks/` (Agent Ops buckets + **`wbs_tasks`** с `/projects`)
2. **Queue** — `GET /api/delivery/queue/?role=backend&status=ready`
3. **Claim** — `POST /api/delivery/tasks/{id}/claim/` (или **auto-claim** при назначении на service account — см. ниже)
4. **Work** — PATCH task fields; journal `POST .../comments/` `{ "kind": "result", "body": "..." }`
5. **Handoff** — `POST /api/delivery/tasks/{id}/handoffs/` with `to_role`, optional `to_user`, `reason`, `expected_next_step`, `done_summary`
5. **Meaning changes** — agents cannot silently rewrite title/outcome; Owner/Planner approve via  
   `POST /api/delivery/tasks/{id}/meaning-changes/{req_id}/review/` `{ "decision": "approve" }`
6. **Ready-gate** — required doc URLs must be set before Ready / claim rules apply

## Auto-claim (service accounts)

При **assign** или **handoff** на service account с `auto_claim_on_assign=true` (по умолчанию для новых агентов) задача сразу переходит в **in_progress** — кнопка Claim не нужна.

Поле на профиле агента: `auto_claim_on_assign`. Человеческие профили по умолчанию `false`.

## Agent runner (Cursor / Codex снаружи)

Fast Plan **не выполняет код** — только ставит задачу и шлёт сигнал. Исполнение в Cursor/Codex.

### Вариант A — poll-скрипт (локально / cron / Docker)

```bash
# один агент
set FAST_PLAN_BASE_URL=http://127.0.0.1:8080
set FAST_PLAN_TOKEN=fp_...
set FAST_PLAN_WORKSPACE_ID=1
python scripts/agent-runner-poll.py

# несколько агентов — scripts/agent-runner.config.example.json
set AGENT_RUNNER_CONFIG=scripts/agent-runner.config.example.json
python scripts/agent-runner-poll.py
```

**Docker (фоновый опрос без чата):**

```bash
# 1) scripts/agent-runner.config.local.json — токены агентов, base_url http://frontend
# 2) в .env: COMPOSE_PROFILES=agents  AGENT_RUNNER_CONFIG=scripts/agent-runner.config.local.json
docker compose --profile agents up -d
```

Скрипт опрашивает `my-tasks` (Agent Ops + WBS) по каждому токену. На новую задачу печатает prompt и опционально POST на `AGENT_RUNNER_CALLBACK_URL`.

Cron: `AGENT_RUNNER_ONCE=1` раз в минуту.

### Вариант B — workspace webhook

Settings → Webhooks → URL (HTTPS) + события:

- `delivery.task.assigned`
- `delivery.task.handoff`

Payload: `{ task, auto_claimed, prompt_hint, workspace_id }`. Ваш runner получает POST и будит нужный чат Cursor (Automations / свой сервис).

### Вариант C — Cursor rule в каждом чате

Rule для Cursor: [`.cursor/rules/cursor-agent-inbox.mdc`](../.cursor/rules/cursor-agent-inbox.mdc) (шаблон для других репо — [`docs/templates/cursor-agent-inbox.mdc`](templates/cursor-agent-inbox.mdc)). Секреты — в env чата. Команда пользователя: «есть задача?» — агент сам ходит в API.

Сценарий заказчика: [CUSTOMER_AGENT_LOOP.md](CUSTOMER_AGENT_LOOP.md).

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

Workspace outbound webhooks (Settings): `delivery.task.assigned`, `delivery.task.handoff` — для agent runner, см. выше.
