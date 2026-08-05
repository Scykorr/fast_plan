# Changelog

Все заметные изменения продукта **Fast Plan** фиксируются в этом файле.

Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/),
версии — [Semantic Versioning](https://semver.org/lang/ru/):

- **MAJOR** — несовместимые изменения API/поведения
- **MINOR** — новая функциональность без ломающих изменений
- **PATCH** — исправления и мелкие улучшения

Источник истины версии: файл [VERSION](VERSION) в корне репозитория.
При релизе обновляйте VERSION, этот файл, rontend/package.json и убедитесь,
что GET /api/health/ отдаёт ту же версию.

## [Unreleased]

### Planned

См. [ROADMAP.md](ROADMAP.md) — S3 Integrations **в перспективе**; Process-as-WBS reparent polish.

## [0.22.0] — 2026-08-05

### Added

- **SLA timers UI** — countdown/overdue badges в process inbox; фильтр `?sla=`; breach board на `/processes?tab=ops` с deep-link в задачу
- **Issue / action log** — `ProjectIssue` CRUD (`/api/projects/<id>/issues/`), вкладка Issues на проекте (отдельно от Risk)
- **Issue badge** — счётчик open high-priority на overview и в табе Issues
- **Ops hygiene** — STAGING § Migrate backlog + Quarterly restore drill; `restore-drill.sh` вызывает `migrate --check`

## [0.21.0] — 2026-08-05

### Added

- **Process-as-WBS S6 хвост** — capacity hint на узлах; CSV/XLSX export дерева; comments на ProcessWorkNode; sibling DnD reorder
- **Quote→WBS** — `POST /api/crm/documents/<id>/create-wbs/` (строки КП → work packages)
- **CRM health lite** — `GET /api/crm/health/?deal_id=` / `organization_id=` + badge на `/deals`

### Changed

- **SMTP go-live ops** — локально verification включён после рабочего Yandex SMTP; staging/prod checklist в STAGING/DEPLOY уточнён

## [0.20.0] — 2026-08-04

### Added

- **Process-as-WBS deepen (S6)** — Kanban-доска на ProcessInstance (карточки ↔ UserTask-узлы); time entries и вложения на ProcessWorkNode; колонки/часы/файлы в дереве на `/processes`; deep-link `/kanban?board=`

## [0.19.0] — 2026-08-04

### Added

- **Process-as-WBS (S5/S6 lite)** — ProcessWorkNode; POST …/instances/<id>/materialize-wbs/; дерево + RACI/даты/Gantt-lite на /processes; highlight BPMN
- **Methodology packs (S7)** — prince2_stage, scrum_ceremony
- **Deal BANT + stage playbook (S7)** — BANT flags, qualification_score, playbook checklist UI на /deals
- **PERT Monte Carlo** — ?method=monte_carlo&trials=; UI toggle
- **Leveling apply-all / undo** — apply/undo API; Gantt + Capacity propose
- **Publish migrate** — migrate_running; SubProcess collapse; Inclusive tip
- **SMTP go-live guards** — go_live_ready, health checks.email; Яндекс в docs/SMTP.md
- **SMTP status / test-send**, guest payment, Inclusive GW, SubProcess children, leveling propose

### Changed

- **Email delivery honesty** — register email_sent; invite resend не ротирует token при SMTP fail; renewals в digest; EMAIL_TIMEOUT + TLS/SSL guard
- **Email verification** — default alse в CI; после SMTP на staging: REQUIRE_EMAIL_VERIFICATION=true
- **Term glossary** — Process-as-WBS, BANT, PRINCE2, Scrum, Monte Carlo, leveling…

## [0.18.0] — 2026-07-31

### Added

- **Deal → Project handoff** — `POST /api/crm/deals/<id>/create-project/` (optional `template_id`); UI на `/deals`
- **Process ops dashboard** — `GET /api/process/ops/` (stuck / aging / SLA); вкладка Ops на `/processes`
- **UserTask ↔ WBS/Kanban binding** — `PATCH /api/process/tasks/<id>/bind/`; на complete → progress 100% + Kanban; UI на `/process-tasks`
- **Guest commercial portal** — `CrmDocumentShareLink`, публичные `GET/POST /api/crm/share/<token>/` (+ `/approve/`, `/pdf/`); UI `/commerce/:token` и кнопка «Ссылка гостю» на `/crm-commerce`
- **Capacity-aware schedule hints** — `capacity_hint` в `GET …/schedule/` и WBS; подсветка перегруза на Gantt/WBS
- **Org/Person merge** — `GET …/duplicates/`, `POST …/merge/`; панель дублей на `/clients`
- **Project change requests** — `GET/POST …/change-requests/`, `POST …/decide/` (approve → linked baseline); UI на вкладке Baseline
- **Quote/Invoice line editor** — multi-line SKU picker, `recompute_amount`, PATCH строк на `/crm-commerce`
- **PERT probabilistic finish** — `finish.p10/p50/p90` (+ dates) в `GET /api/projects/<id>/pert/`; подпись на PERT UI
- **Service-adapter catalog** — `GET /api/process/adapters/` (+ executable elements); вкладка Adapters на `/processes`
- **BPMN expansion (lite)** — catalog: Inclusive GW experimental, SubProcess planned; timers уже были
- **CRM → process events** — `activity.created` / `document.accepted` (+ `deal.stage_changed`) стартуют definitions по `category`; automation triggers + action `start_process`
- **Contract renewals / ARR lite** — поля `renewal_date` / `term_months` / `arr_annual`; `GET /api/crm/renewals/`; UI на `/crm-commerce`
- **Activity → WBS/Process spawn** — `POST /api/crm/activities/<id>/spawn/`; кнопки на `/clients`
- **1С ↔ SKU sync lite** — `pending_skus`/`nomenclature` → upsert `CrmSku` + `external_ref`
- **Cross-project dependencies** — `CrossProjectDependency`, `GET/POST/DELETE /api/workspace/cross-dependencies/`; UI на `/portfolio`

## [0.17.0] — 2026-07-31

### Added

- **Склад / SKU** — `CrmSku` + `CrmStockMovement`; CRUD `/api/crm/skus/`, adjust/movements; `sku_id` в `line_items`; списание при invoice→paid и возврат при void; UI на `/crm-commerce`

### Changed

- **Staging smoke** — CRM custom fields create/list + auto-enable Agent Ops delivery APIs; `GET /api/crm/skus/`; `FRONTEND_HOST_PORT` for compose when host `:8080` is taken
- **Health** — expose `settings.REDIS_URL` so `GET /api/health/?extended=1` reports redis ok when configured

### Ops

- **2026-07-29 staging drill** — migrate `0013_custom_fields_016`, smoke 33/33 (custom fields + Agent Ops), restore-drill 123 tables — see [`STAGING.md`](STAGING.md) § Ops log
- **2026-07-31 release deploy** — staging compose rebuild; `0014_sku_inventory_016` applied; smoke **34/34** at version `0.17.0`

## [0.16.0] — 2026-07-29

### Added

- **CRM custom fields** — definitions + values for organization/person/deal/lead; UI on CRM cards; `GET/POST /api/crm/custom-fields/`, `PUT /api/crm/{target}/{id}/custom-fields/`
- **Typed CRM SDK** — `packages/crm-client` (`@fast-plan/crm-client`); OpenAPI via `drf-spectacular` (`GET /api/schema/`, `/api/docs/`); CI `openapi-typescript` codegen
- **Agent Ops hardening** — `docs/AGENT_OPS.md`; richer Agents onboarding + curl snippets; CI `E2E_AGENT_OPS=1` claim→handoff→meaning; agent profile upsert
- **Telephony PBX polish** — Beeline Cloud / MTS backends (dial + webhook normalize, recording_url)
- **Ops** — `scripts/restore-drill.sh` non-destructive staging restore drill (see DEPLOY.md §5.3)

### Fixed

- **CRM calendar test** — mid-month fixture dates (end-of-month flake when `close_date` crossed into next month)
- **Agent Ops E2E** — set task `ready` + pass `version` before claim

### Planned

См. [ROADMAP.md](ROADMAP.md).

## [0.15.0] — 2026-07-28

### Added

- **P9 Agent Ops** — модуль `delivery` (Epic/Sprint/DeliveryTask, Ready-gate, claim/handoff, ACL, GitHub multi-PR + Checks, meaning Owner/Planner approve, access log, service accounts); UI `/agent-ops` + onboarding агентов
- **CRM polish** — hotkeys на `/deals` `/leads` `/clients`; saved filters; PDF **Акт**; Instagram/VK → Activity; report builder + CSV; GraphQL read lite (`POST /api/crm/graphql/`)
- **Ops** — `scripts/backup-db.sh` (pg_dump + optional GPG); staging smoke для `/api/delivery/` при `agent_ops_enabled`; E2E Agent Ops smoke
- **DEPLOY.md** — self-hosted Docker Compose install, upgrades without data loss, backup/restore

### Planned

См. [ROADMAP.md](ROADMAP.md) — следующий фокус: MS Project XML (нужен sample), склад только по запросу.

## [0.14.2] — 2026-07-26

### Added

- **Click-to-call on Lead** — «Позвонить» on `/leads`; dial records `lead_id` in Activity body
- **Live Asterisk ARI WebSocket bridge** — `python manage.py run_ari_bridge` (+ docker compose profile `telephony`); `GET /api/crm/connectors/<id>/ari-bridge/` status; ingest ARI events into telephony Activities

## [0.14.1] — 2026-07-26

### Added

- **Mango VPBX webhook sign** — verify `sha256(api_key + json + api_salt)` on telephony webhooks when `pbx=mango`; clearer inbound/outbound from Mango `from`/`to` parties
- **Asterisk AMI/ARI event ingest** — normalize `ChannelStateChange` / Hangup / batch `events[]` (not only CDR); noise events skipped
- **Click-to-call** — «Позвонить» on Person (`/clients`) and Deal detail (`/deals`); dial links `person_id` / `deal_id`; deals expose `person_phone`

## [0.14.0] — 2026-07-26

### Added

- **Calendar 2-way (1e)** — pull + push sync for Outlook/Google; `conflict_policy` (ours/theirs/manual); `CalendarSyncConflict` queue + resolve API; Settings UI Sync both / Pull / conflict resolve
- **Telephony / PBX (10)** — webhook → `Activity(kind=call)`; outbound dial via **Asterisk ARI**, **Mango Office** VPBX callback, or generic `dial_url`; UI on `/crm-commerce`
- **CRM connectors (10)** — Stripe / 1C / WhatsApp / SMS (`IntegrationConnector`), catalog + CRUD + sync/send, public webhooks `/api/crm/connectors/webhooks/<provider>/<token>/`
- **CRM finance deep (6)** — AP bills (`doc_type=bill`), extended AR/AP summary, P&L by org/deal (`GET /api/crm/finance/pnl/`), cashflow forecast (`GET /api/crm/cashflow-forecast/`); payments create linked `finance.Transaction`
- **CRM roles expand (9)** — `crm_role`: `accounting`, `marketing` (+ Settings UI); marketing in lead assignee pool
- **CRM tasks UX (1f)** — priority / checklist / repeat on DealTask; LeadTask; unified Kanban board `GET/PATCH /api/crm/tasks/board/`; page `/crm-tasks`
- **Staging smoke 0.14** — calendar providers/connections/conflicts + connectors catalog (telephony)

## [0.13.0] — 2026-07-26

### Fixed

- **Chat** — emoji/GIF reaction picker via portal (no overflow clip), scrollable list; compact horizontal layout (messages + composer side-by-side on wide screens); guest chat matches the same layout
- **Calendar tests** — mock `getCrmEvents` in `WorkspaceCalendar` unit test (CI regression after CRM calendar)

### Added

- **P8g Process advanced** — mining lite (`GET /api/process/mining/` DFG/paths/bottlenecks), OMG DMN decisionTable FEEL-lite + DMN UI tab, richer CMMN (`depends_on` / `required` / `available_items` / gated close); ADR updated
- **CRM calendar** — deal tasks / meetings / close dates on `/calendar`; Outlook + Google Calendar OAuth push sync (Settings); `GET /api/calendar/crm/`
- **Staging smoke 0.12** — SSO providers check, process metrics/mining/DMN/CMMN/packs, CRM calendar API

### Changed

- **Process UX** — per-task notes, approve/reject on inbox; link processes ↔ tasks
- **SSO** — вход через Google временно отключён; остаётся Microsoft OAuth
- **ROADMAP CRM matrix** — статусы 15 блоков сверены (P6a–P6i + calendar sync ✓); явный CRM backlog (1f/6/9/10)

## [0.12.0] — 2026-07-23

### Fixed

- **CI** — mock `window.matchMedia` in Vitest; ship `VERSION` into backend Docker image; insecure cookies when `DJANGO_SECURE_SSL_REDIRECT=false`; CSRF on smoke AI draft; PWA SW register outside auth; e2e login locator strict-mode

### Added

- **P7 Security SSO** — Google/Microsoft OAuth (`SocialAccount`, `/api/auth/oauth/…`, login buttons; 2FA redirect with `pre_auth_token`); env `OAUTH_*` / `OAUTH_REDIRECT_BASE`
- **P8 Process UX** — bpmn-js Modeler, instance token highlight (`active_element_ids`), XOR approval pack, deep-links Deal/Project from process tasks
- **P8 Process** — BPMN 2.0 (SpiffWorkflow) + bpmn-js viewer, user-task inbox, DMN lite, CMMN-lite cases, compliance packs (ISO 9001/PDCA, ITIL Change, NIST Incident), import/export, P6e→BPMN migrate, metrics; pages `/processes`, `/process-tasks`; ADR [`docs/adr-p8-process.md`](docs/adr-p8-process.md)
- **P7 Mobile** — Web Push (VAPID + `PushSubscription`, SW `push-sw.js`), offline queue for CRM activities/deal tasks, Settings «Мобильное / PWA»; `manage.py generate_vapid_keys`
- **Redis SSE pub/sub** — `workspaces.events` публикует в Redis при `REDIS_URL` (multi-worker gunicorn); fallback in-process без Redis
- **P7 Security MVP** — TOTP 2FA (setup/enable/disable/verify + backup codes), `AuthSession` list/revoke, workspace IP allowlist middleware + API; UI в Settings и шаг 2FA на login; [`SECURITY.md`](SECURITY.md) runbook
- **P6g Omnichannel** — IMAP + Telegram → Activity (`channel`/`direction`/`external_id`), ChannelConnection CRUD/sync, Telegram webhook, Celery `crm.sync_channels`
- **P6h Commerce** — Quote/Invoice/Contract + PDF, payments, AR lite; страница `/crm-commerce`
- **P6i CRM analytics** — conversion, avg check, by owner/source, LTV/CAC lite, saved reports; страница `/crm-analytics`
- **P6f AI CRM** — insights (stale clients / at-risk deals + forecast), draft email/КП, activity summary, suggest/create deal tasks; страница `/crm-ai`; OpenAI/Ollama/heuristics
- **Automations visual editor** — конструктор conditions/actions вместо JSON preview; CRUD правил в UI
- **schedule.daily** — триггер + шаблон `stale_deal_daily`, Celery beat `crm.run_daily_automations`, `skip_if_open` для задач
- **P6e BPM-lite** — `AutomationRule` (trigger/conditions/actions), templates form_lead + follow_up_2d, deferred delay queue, runs log, страница «Автоматизации»
- **Deals UX** — convert lead → `/deals?deal=`; same-column DnD persists reindexed `position` via `apply_deal_move`
- **P6d Leads** — Lead entity, CSV/API import, round-robin/manual assign, email/phone dedupe, rules-based score, convert→Deal; страница «Лиды»
- **P6c Deals** — pipeline stages, Deal (amount/probability/close_date), forecast, deal tasks + reminders, Deal↔Org/Project, Finance `organization`/`deal` counterparty; страница «Сделки»
- **Clients owner UI** — назначение менеджера (`owner`) из карточки клиента
- **P6b Client card MVP** — telegram/whatsapp/social_urls, tags & segments, comments & file attachments, owner manager, activity kinds `invoice`/`order`, workspace `crm_role`, Clients UI card tabs + «нет касаний N дней»
- **Staging checklist** — [`STAGING.md`](STAGING.md): SMTP verification, webhooks, PWA install/update, smoke-тесты
- **Extended health** — `GET /api/health/?extended=1` (database, redis, email backend, celery_eager)
- **AI WBS/schedule drafts** — target `wbs` в `POST /api/projects/<id>/ai-draft/`, применение через `POST …/ai-draft/apply/`, UI на Project Overview
- **Per-project AI prompts** — поле `Project.ai_prompts`, автосохранение промпта при генерации, префилл в UI
- **Итеративное уточнение WBS** — `refinement` + `current_draft` в ai-draft API, кнопка «Уточнить черновик» в диалоге
- **Staging smoke script** — `node scripts/staging-smoke-check.mjs` (health, extended checks, optional auth/PWA/share)
- **Ollama LLM** — локальные AI-черновики через `OLLAMA_BASE_URL` / `OLLAMA_MODEL` (приоритет ниже OpenAI)
- **CI staging smoke** — job `staging-smoke` поднимает docker-compose и прогоняет полный smoke-check
- **Smoke fixtures** — `python manage.py ensure_smoke_fixtures --json` для CI/staging
- **Blue/gray theme** — светлая палитра blue→white и тёмная soft-gray вместо terracotta; быстрый переключатель темы в шапке
- **System theme** — режим «Как в системе» с live-слушателем `prefers-color-scheme`
- **Auth hero gradient** — мягкий градиент синий→белый (и dark-вариант) на login/register и смежных auth-страницах
- **Light calendar contrast** — дни недели и даты читаемые; фон страницы чуть сильнее tinted blue, заголовок сетки на `cream`
- **P5 Чаты** — project/workspace chat rooms, модерация (open/disabled/announcements/mute), сообщения с вложениями, пересылка, вкладка «Чат» на проекте и чат портфеля, SSE `chat.message` + уведомления
- **Chat extensions** — DM 1:1, ответы (reply_to), реакции, голосовые, гостевой чат через share-link (`allow_chat` / `chat_can_post`), edit/delete модератором, авто-архивация disabled-чатов (Celery beat)
- **Ollama в docker-compose** — опциональный profile `ai` (`ollama` + `ollama-init` pull модели); см. `STAGING.md` / `.env.example`
- **E2E Playwright** — пакет `e2e/` (login, PWA manifest/SW, SSE toast smoke) + CI job `e2e`
- **Chat reaction picker** — emoji grid + GIF (curated Giphy + HTTPS URL allowlist)
- **DM E2E encryption** — ECDH P-256 identity keys, AES-GCM ciphertext in DM bodies; server stores opaque wraps only
- **E2E recovery phrase** — 12-word phrase encrypts identity backup (`recovery_blob`) for multi-device sync; UI in Settings
- **E2E DM media** — attachments and voice encrypted client-side before upload; metadata in ciphertext envelope
- **P6 Project CRM (start)** — эпик в ROADMAP; P6a: app `crm` (Organization/Person/Activity), страница «Клиенты», `Project.client_organization`
- **P6 backlog sync** — ROADMAP: матрица 15 блоков требований CRM → фазы P6b–P6i + P7 Security/Mobile; явный out-of-scope

## [0.11.0] — 2026-07-20

### Added

- **Per-project roles UI** — панель «Участники проекта» на Project Overview (добавление, смена роли, удаление)
- **Jira CSV import** — `POST /api/projects/<id>/import/` с `format=jira` (Issue key, Summary, Parent key); выбор формата в UI Project Overview
- **AI drafts UI** — кнопки «AI-черновик рисков» и «AI-черновик устава» с превью и применением на странице проекта
- **P3 hardening**: toast обновления PWA (`PwaUpdatePrompt`), повторная отправка письма подтверждения email в Settings, тестовая доставка webhook (`POST /api/workspace/webhooks/<id>/test/`)

### Tests

- `tests/test_p4_features.py` — Jira CSV import (unit + API)
- `tests/test_integrations_api.py` — webhook test delivery

## [0.10.0] — 2026-07-20

### Added

- **Мультивалюта**: `GET/PATCH /api/workspace/settings/`, CRUD `/api/workspace/exchange-rates/`, `GET /api/workspace/fx/convert/`; конвертация сумм в Finance/Portfolio через базовую валюту workspace и курсы; UI управления курсами в Settings (owner)

## [0.9.0] — 2026-07-20

### Added

- **CSV import**: WBS (`POST /api/projects/<id>/import/`) и транзакции Finance (`POST /api/finance/transactions/import/`) с теми же колонками, что у экспорта; кнопки импорта на Project Overview и Finance
- **Guest share links**: `ProjectShareLink`, CRUD для editor+, публичный `GET /api/share/<token>/` и страница `/share/:token` с read-only статус-отчётом
- **PERT / сетевой график**: `GET /api/projects/<id>/pert/` (узлы O/M/P, expected duration, критический путь); вкладка PERT на странице проекта (ReactFlow)
- **AI-черновики**: `POST /api/projects/<id>/ai-draft/` для risks и charter (OpenAI или эвристика)
- **Per-project roles**: `ProjectMember` (manager/contributor/viewer) и `has_project_min_role` поверх workspace RBAC
- **Мультивалюта (foundation)**: `Workspace.currency`, модель `ExchangeRate` (API/UI конвертации — в следующем релизе)

### Tests

- `tests/test_p4_features.py` — 18 кейсов: import, share, pert, AI drafts, project roles

## [0.8.0] — 2026-07-19

### Added

- **Аккаунт**: обязательное подтверждение email при регистрации, безопасная повторная отправка ссылки, редактирование username/имени/фамилии и загрузка аватара до `AVATAR_MAX_BYTES`
- **Интеграции**: исходящие HTTPS-webhooks для событий рисков и приближающихся дедлайнов; HMAC-SHA256 подпись, Celery-доставка с retry, защита от private/loopback URL, журнал последних доставок
- **API tokens**: одноразовый показ токена, хранение SHA-256 hash, scopes `read`/`write`, привязка к workspace, срок действия/отзыв и owner-only управление в Settings
- **Локализация и валюта**: `LocaleContext`, русская локаль по умолчанию, английский каркас для навигации, выбор RUB/USD/EUR и единое форматирование денежных значений
- **Тёмная тема**: сохраняемая warm-dark palette для всех семантических цветов интерфейса
- **PWA**: manifest, service worker с auto-update, offline app shell и cache шрифтов через `vite-plugin-pwa`
- **Kanban analytics**: история переходов карточек, `GET /api/boards/<id>/analytics/`, burndown за 14 дней и velocity за 4 недели
- **Шаблоны проектов**: сохранение WBS, tracker/status references и Kanban-колонок существующего проекта; создание нового проекта из шаблона

### Security

- Новые пользователи не могут получить JWT до подтверждения email; существующие аккаунты миграцией помечаются подтверждёнными
- Webhook endpoints принимают только HTTPS и перед доставкой проверяются на публичный IP
- API-токены не могут управлять токенами/webhooks и автоматически теряют доступ после удаления создателя из workspace

## [0.7.0] — 2026-07-19

### Added

- **Audit log**: приложение `audit` — модель `AuditLogEntry` (workspace, actor, action, entity_type/id, summary, changes JSON), неизменяема (нет update/delete в API); хелпер `log_audit(...)`; вызовы из создания/удаления инвайтов, смены роли/удаления участника, create/update/delete транзакций, WBS-узлов и рисков; `GET /api/workspace/audit/?page=` (owner/editor); страница `/audit`
- **Вложения**: приложение `attachments` — модель `WorkItemAttachment` (`file`, `uploaded_by`, `wbs_node` XOR `card` через `CheckConstraint`, `name`, `size`, `content_type`); лимит `ATTACHMENT_MAX_BYTES`; `GET/POST /api/wbs/<id>/attachments/`, `GET/POST /api/cards/<id>/attachments/`, `DELETE /api/attachments/<id>/`; медиа отдаётся через `MEDIA_URL`/`MEDIA_ROOT` в DEBUG; список + загрузка файлов на панели деталей WBS-задачи
- **Учёт трудозатрат**: приложение `timelog` — модель `TimeEntry` (workspace, user, wbs_node, hours, work_date, notes); CRUD `GET/POST /api/workspace/time-entries/`, `PATCH/DELETE .../<id>/`; `build_capacity_report` дополнен полем `logged_hours` (фактические часы из `TimeEntry` за неделю) как ориентир по факту относительно `capacity_hours`/`allocated_hours`; форма логирования времени и список записей на панели деталей WBS-задачи
- **Экспорт**: `openpyxl` для XLSX; `GET /api/projects/<id>/export/?output=csv|xlsx` (WBS flatten), `GET /api/finance/transactions/export/?format=csv|xlsx`, `GET /api/projects/<id>/milestones.ics` и `GET /api/workspace/calendar.ics` (вехи/дедлайны в формате iCalendar); кнопки экспорта CSV/XLSX на Finance и Project Overview, .ics на Calendar и Project Overview
- **Realtime (SSE)**: `GET /api/workspace/events/` (`StreamingHttpResponse`, `text/event-stream`), in-process pub/sub по `workspace_id` (см. ограничение однопроцессности в докстринге `workspaces/events.py`); `publish_event(...)` при перемещении Kanban-карточки, обновлении WBS-узла и создании комментария; хук `useWorkspaceEvents` (EventSource с cookie-авторизацией) + toast «Данные обновлены» в `AppLayout`
- **Celery + Redis**: `backend/config/celery.py`, задача `run_reminders` (обёртка над `run_all_reminders`), беат-расписание раз в час; `docker-compose` сервисы `redis`, `celery-worker`, `celery-beat` вместо shell-`scheduler`; cache-lock (Redis либо locmem) в `send_reminders`, защищающий от параллельного запуска
- Портфельный обзор (`PortfolioPage`, `/portfolio`) — сводка SPI/CPI, просрочек и бюджета по всем проектам workspace
- `.env.example`: `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, `CELERY_TASK_ALWAYS_EAGER`, `SENTRY_DSN`, `ATTACHMENT_MAX_BYTES`, `LOG_LEVEL`

### Changed

- `docker-compose.yml`: `redis` сервис + volume `redis_data`; `celery-worker`/`celery-beat` заменяют предыдущий `scheduler`

## [0.6.0] — 2026-07-19

### Added

- Budget vs actual на Overview проекта и Finance (фильтр по проекту) через `getProjectFinance`
- Управление приглашениями: `DELETE /api/workspace/invitations/<id>/` и `POST .../resend/` + кнопки в Settings
- Редакторы Risk / Stakeholder / Baseline: PATCH `/api/risks/<id>/`, `/api/stakeholders/<id>/`, PATCH/DELETE `/api/baselines/<id>/` + inline edit-формы (RiskRegister, StakeholderPanel) и выбор/переименование/удаление baseline (BaselineView)
- Уведомления: пагинация через DRF `PageNumberPagination` и `POST /api/notifications/mark-all-read/`; в `NotificationBell` — кнопки «Показать ещё» и «Прочитать все»
- Уведомления о комментариях: типы `COMMENT` (assignee WBS-узла/карточки) и `MENTION` (`@username` в тексте комментария); дедупликация, автор не уведомляется
- `CommentThread`: автокомплит `@username` по участникам workspace
- `ConfirmDialog` + `useConfirm` — единый a11y-диалог подтверждения вместо `window.confirm` (Admin, Calendar, Finance, ProjectDetail WBS, Kanban колонки и карточки)
- CI: `--cov-fail-under=80` для backend, `npm run lint` и `npm run typecheck` для frontend, отдельный job проверки синхронизации версий (`scripts/check-version-sync.mjs`)

### Changed

- `NotificationListView` возвращает пагинированный envelope (`results`/`count`/`next`/`previous`) вместо плоского массива
- `WorkspaceMemberListView` отдаёт `username` участников (нужен для автокомплита упоминаний)

## [0.5.0] — 2026-07-19

### Added

- SMTP email: `EMAIL_*` / `FRONTEND_BASE_URL`, хелпер `notifications/mail.py`, шаблоны invitation / password_reset / reminder_digest
- Письма приглашений в workspace при create (с upsert повторного invite)
- Digest-письма напоминаний из `send_reminders` (не чаще 1/user/day)
- Восстановление пароля: `POST /api/auth/password/forgot|reset/` + страницы `/forgot-password`, `/reset-password`
- Смена пароля: `POST /api/auth/password/change/` + форма в Settings
- Inline-формы вместо `window.prompt`: проект, WBS add/rename, риски, стейкхолдеры, baseline, Kanban card/column
- RACI: явный выбор WBS-узла, стейкхолдера и типа R/A/C/I

### Changed

- Invite create: update-or-create по `(workspace, email)` вместо IntegrityError при повторной отправке

## [0.4.0] — 2026-07-19

### Added

- PDF и digest статус-отчёта проекта (`/export/?output=pdf` + UI на Overview)
- Комментарии / лог решений на WBS (`WorkItemComment`) и API для карточек
- Глобальный поиск: `GET /api/workspace/search/` + search bar в header
- «Мои задачи»: `GET /api/workspace/my-tasks/` и страница `/tasks`
- Capacity по неделе: `GET/PATCH /api/workspace/capacity/` и страница `/capacity`
- P3 UI: status report digest, WBS comment thread, global search bar
- Страницы «Мои задачи» (`/tasks`) и Capacity (`/capacity`)
- Активный workspace: `User.active_workspace`, API `GET /api/workspaces/`, `POST /api/workspaces/<id>/activate/`
- Заголовок `X-Workspace-Id` для явного выбора пространства
- UI switcher workspace в sidebar и на странице настроек
- Страница принятия приглашения `/invite/:token` с возвратом после login/register
- Копирование ссылки приглашения в Settings
- RBAC: Viewer — только чтение; Editor — рабочие данные; Owner — участники, приглашения и tracking-настройки
- Командный дашборд: `GET /api/workspace/dashboard/` (просрочки, риски, SPI/CPI, непрочитанные)
- Workspace FK у Notification + deep-link URL в уведомлениях
- Deep-link query params (`workspace`, `tab`, `node`, `card`, `risk`, `assignee`, `status`, `project`) на Project Detail и Kanban
- Клиентские фильтры WBS/Kanban по исполнителю и статусу с записью в URL
- Формы Finance (`TransactionForm` с типом/датой/категорией/проектом) и invite в Settings
- Метаданные WBS на Kanban-карточках (assignee/status/wbs_node_id)
- CI coverage для `projects`, `finance`, `tracking`, `notifications`
- Фоновые напоминания: `manage.py send_reminders` + Docker `scheduler`
- `Notification.dedupe_key` для идемпотентных birthday/milestone/deadline alerts

### Changed

- Администрирование tracking: inline-формы вместо `window.prompt` для трекеров, статусов, полей и enumerations
- Дашборд — командный центр вместо только приветствия и ДР
- Единый `WorkspaceMixin` и permission-классы в `workspaces/`
- После accept invitation активный workspace переключается автоматически
- GET charter/dashboard/tracking-metadata без лишних side-effect записей для viewer
- JWT access/refresh в HttpOnly cookies + CSRF на mutating API; токены убраны из `localStorage`
- Production: fail-closed `SECRET_KEY`, HSTS/secure cookies, секреты только через `.env`

## [0.3.0] — 2026-07-19

### Added

- Трекеры, статусы и кастомные поля (типы: строка, текст, int/float, процент, bool, дата/datetime, список, связанные списки, пользователь, URL, email)
- Администрирование workspace: трекеры, статусы, поля
- Панель деталей задачи/проекта в WBS с кастомными значениями
- Тесты optimistic DnD-логики Kanban и регистрации → доска по умолчанию
- Тест рендера событий FullCalendar
- WhiteNoise + `collectstatic` для статики Django в Docker
- Node 22 в frontend Docker-образе (как в CI)
- Endpoint здоровья с версией продукта: `GET /api/health/`

### Changed

- CI: strict TypeScript, Node 22
- CORS в Docker учитывает порт frontend `:8080`

## [0.2.0] — 2026-07

### Added

- Проекты: WBS (mind-map), Gantt, двусторонняя синхронизация с Kanban
- PMBOK: риски, стейкхолдеры, устав, RACI, baseline, CPM
- Финансы, уведомления, настройки workspace и приглашения (API)
- Drag-and-drop узлов WBS

## [0.1.0] — 2026-06

### Added

- Auth (JWT): регистрация, логин, workspace по умолчанию
- Kanban: доски, колонки, карточки, move API, DnD UI
- Календарь дней рождения: контакты, FullCalendar, виджет ближайших ДР
- Тёплая тема UI, адаптивный sidebar/drawer
- Docker Compose (PostgreSQL + backend + frontend/nginx)
- GitHub Actions CI (pytest + vitest + build)
