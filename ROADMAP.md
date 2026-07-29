# Roadmap / улучшения

Живой бэклог Fast Plan. Приоритет сверху вниз (P0 → P4).
При реализации пункта: запись в `CHANGELOG.md` → `[Unreleased]`, затем вычеркнуть здесь или перенести в «Выполнено».

Оценка scope: **S** — часы/день, **M** — несколько дней, **L** — неделя+.

---

## Выполнено

| Когда | Что |
|-------|-----|
| 2026-07-19 | **P0** invite UI, RBAC owner/editor/viewer, workspace switcher |
| 2026-07-19 | **P1** командный дашборд, формы Finance/Admin/Settings, deep-links и фильтры WBS/Kanban |
| 2026-07-19 | **P2** CI coverage apps, production hardening, HttpOnly JWT + CSRF, фоновые reminders |
| 2026-07-19 | **P3** PDF/digest отчёт, комментарии/решения, поиск + «Мои задачи», capacity по неделе |
| 2026-07-19 | Релиз **v0.4.0** |
| 2026-07-19 | **P0 (v0.5.0)** SMTP email + invite/digest, forgot/reset/change password, убраны `window.prompt`, RACI с явным выбором |
| 2026-07-19 | **P1 (v0.6.0)** budget UI, revoke/resend invite, редакторы Risk/Stakeholder/Baseline, mark-all-read + пагинация уведомлений, comment-уведомления (@mention), `ConfirmDialog`, CI hardening |
| 2026-07-19 | Релиз **v0.6.0** |
| 2026-07-19 | **P2 (v0.7.0)** audit log, вложения файлов, time entries, экспорт CSV/XLSX/ICS, SSE realtime, Celery/Redis, портфельный обзор, observability (LOGGING + Sentry) |
| 2026-07-19 | Релиз **v0.7.0** |
| 2026-07-19 | **P3 (v0.8.0)** email verification/profile, webhooks, API tokens, i18n/currency, dark theme, PWA, burndown/velocity, project templates |
| 2026-07-19 | Релиз **v0.8.0** |
| 2026-07-20 | **P4 (v0.9.0)** CSV import, guest share links, PERT, AI drafts, per-project roles, frontend P4 UI |
| 2026-07-20 | Релиз **v0.9.0** |
| 2026-07-20 | **Мультивалюта (v0.10.0)** FX settings, exchange rates, конвертация Finance/Portfolio |
| 2026-07-20 | Релиз **v0.10.0** |
| 2026-07-20 | **v0.11.0** Jira CSV import, AI drafts UI, P3 hardening (PWA update, email resend, webhook test), per-project roles UI |
| 2026-07-20 | Релиз **v0.11.0** |
| 2026-07-20 | **Staging checklist** (`STAGING.md`), extended health, AI WBS/schedule drafts, per-project AI prompts |
| 2026-07-20 | **AI WBS refine** в диалоге + `scripts/staging-smoke-check.mjs` |
| 2026-07-20 | **Ollama LLM** для AI-черновиков + CI job `staging-smoke` (docker-compose) |
| 2026-07-20 | **Blue/gray theme** + system preference + auth hero gradient |
| 2026-07-20 | **P5 Чаты** — project/workspace chat, ACL, модерация, forward, UI |
| 2026-07-22 | **Redis SSE pub/sub** + **P7 Security MVP** (2FA, sessions, IP allowlist) |
| 2026-07-22 | **P7 Mobile** — Web Push + offline CRM queue |
| 2026-07-23 | **P8 Process** — эпик BPMN/DMN/CMMN + ADR SpiffWorkflow/bpmn-js |
| 2026-07-23 | Релиз **v0.12.0** — SSO Microsoft, P8 UX, P7 Mobile/Security в changelog |
| 2026-07-25 | **CRM calendar sync** — events + Outlook/Google push; staging smoke 0.12 |
| 2026-07-25 | **Матрица CRM-требований** обновлена (P6a–P6i ✓, backlog 1f/6/9/10) |
| 2026-07-26 | Релиз **v0.14.2** — Lead click-to-call, live ARI WebSocket bridge |
| 2026-07-26 | Релиз **v0.14.1** — Mango sign, Asterisk AMI/ARI ingest, click-to-call Person/Deal |
| 2026-07-26 | Релиз **v0.14.0** — calendar 2-way, telephony Asterisk/Mango, CRM connectors/finance/roles/tasks |
| 2026-07-26 | **Calendar 2-way + telephony** — pull/conflict policy; PBX connector → Activity |
| 2026-07-26 | Релиз **v0.13.0** — P8g, CRM calendar sync, chat UX, staging smoke 0.12 |
| 2026-07-26 | **CRM tasks UX (1f)** — priority/checklist/repeat, LeadTask, `/crm-tasks` Kanban |
| 2026-07-26 | **CRM finance deep (6)** + **roles expand (9)** — AP/P&L/cashflow; accounting/marketing |
| 2026-07-26 | **CRM connectors (10)** — Stripe / 1C / WhatsApp / SMS webhooks + sync |
| 2026-07-27 | **P9 Agent Ops** — модуль `delivery`, TZ end-to-end (P9a–e) |
| 2026-07-27 | **P9f–g** — ACL/timeline/deps, meaning-approve, webhook HMAC, project create |
| 2026-07-28 | **P9h** — multi-PR GitHub links, Checks webhook, auto-attach, field ACL, timeline `created` |
| 2026-07-28 | **Матрица CRM-требований** актуализирована (ядро закрыто; polish backlog) |

---

## P0 — дыры, мешающие реальному использованию

_Выполнено (2026-07-19 / v0.5.0)._

---

## P1 — ценность из уже написанного API + полировка PM

_Выполнено (2026-07-19 / v0.6.0)._

---

## P2 — коллаборация, отчётность, эксплуатация

_Выполнено (2026-07-19 / v0.7.0)._

- [x] **Realtime** — SSE (`GET /api/workspace/events/`, in-process pub/sub) для card move / WBS update / комментариев + `useWorkspaceEvents` и toast на фронте. **L**
- [x] **Вложения файлов** — `WorkItemAttachment` (WBS work packages и Kanban-карточки), лимит `ATTACHMENT_MAX_BYTES`, UI на панели WBS-детали. **M**
- [x] **Учёт фактических трудозатрат** — `TimeEntry` (workspace/user/wbs_node/hours/date), CRUD API, `logged_hours` в `build_capacity_report`, форма+список на панели WBS-детали. **L**
- [x] **Портфельный обзор** — `PortfolioPage` (`/portfolio`) со сводкой по всем проектам workspace. **M**
- [x] **Экспорт** — CSV/XLSX для WBS и транзакций Finance, ICS для вех проекта и календаря workspace + кнопки в UI. **M**
- [x] **Observability** — structured `LOGGING` + опциональный Sentry (`SENTRY_DSN`). **S**
- [x] **Audit log** — неизменяемый `AuditLogEntry` для member/invitation/finance/WBS/risk мутаций, `GET /api/workspace/audit/`, страница `/audit`. **M**
- [x] **Фоновые задачи** — Celery + Redis (`backend/config/celery.py`, `run_reminders` task, beat schedule раз в час), cache-lock fallback для `send_reminders` без Redis. **M**

---

## P3 — продукт «на вырост»

_Выполнено (2026-07-19 / v0.8.0)._

- [x] **Email verification** при регистрации + редактирование профиля (имя, аватар). **M**
- [x] **Интеграции** — исходящие HTTPS webhooks на дедлайны и риски, HMAC-подпись и журнал доставок. **L**
- [x] **API tokens** для внешних клиентов (machine-to-machine) с scope по workspace. **M**
- [x] **i18n** — `ru` по умолчанию, каркас `en` для shell-навигации; выбор валюты RUB/USD/EUR. **L**
- [x] **Тёмная тема** — soft-gray dark + blue→white light (переключатель в шапке и Settings). **M**
- [x] **PWA / offline-friendly** shell для мобильного просмотра задач и уведомлений. **L**
- [x] **Burndown / velocity** по переходам между Kanban-колонками. **M**
- [x] **Шаблоны проектов** — создать проект из типового WBS/трекеров/Kanban-колонок. **M**

---

## P4 — идеи на потом

_Выполнено (2026-07-20 / v0.9.0–v0.11.0)._

- [x] **Импорт CSV** — WBS и транзакции Finance (backend + UI). **M**
- [x] **Импорт Jira CSV** — экспорт Issue key / Summary / Parent key → WBS; MS Project XML отложен. **M**
- [x] **PERT / сетевой график** — API + вкладка PERT на странице проекта. **M**
- [x] **Гостевой статус-отчёт** — share links, `/share/:token`, панель управления. **M**
- [x] **AI-черновики** — risks/charter API + UI на странице проекта. **M**
- [x] **Per-project roles** — `ProjectMember` + UI на Project Overview. **M**
- [x] **Мультивалютность и курсы** — API settings/exchange-rates, конвертация в Finance/Portfolio. **M**
- [x] **P3 hardening** — PWA update toast, повторная отправка email verification, тест webhook из Settings. **S**

---

## Как выбирать следующий спринт

_Выполнено (2026-07-20): staging checklist, AI WBS/schedule, per-project prompts, WBS refine, smoke script, Ollama LLM, CI staging-smoke, Ollama compose profile `ai`, E2E Playwright + CI job `e2e`, P5 чаты._

Рекомендуемый порядок после v0.11.0:

1. ~~**MS Project XML import**~~ — отложено до появления образца `.mpp`/XML.
2. ~~**Ollama / локальный LLM**~~ — `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, приоритет после OpenAI.
3. ~~**Staging smoke в CI**~~ — job `staging-smoke` + `ensure_smoke_fixtures`.
4. ~~**Ollama в docker-compose**~~ — profile `ai`: `ollama` + `ollama-init`.
5. ~~**E2E Playwright**~~ — `e2e/` + CI job `e2e` (login, PWA, SSE toast).

Следующие кандидаты:

1. ~~**P9 Agent Ops**~~ — закрыт по ТЗ (P9a–h); **релизён в v0.15.0**.
2. ~~**CRM polish**~~ — hotkeys, saved filters, акт PDF, Instagram/VK, report builder, GraphQL lite — **в v0.15.0**.
3. ~~**CRM custom fields + typed SDK + Agent Ops hardening + PBX polish**~~ — **релизён в v0.16.0**.
4. **MS Project XML import** — при появлении подтверждённого формата/образца.
5. ~~**Process conformance / full FEEL / Camunda-grade CMMN**~~ — **явный out of scope** (см. P8 ADR / таблицу «Не цель» ниже). Не планируем как спринт.

~~Ранее закрыто:~~ P5 чаты · Redis SSE · **P6 CRM (ядро + polish + custom fields)** · P7 Security+SSO · P7 Mobile · P8 Process MVP+UX+P8g · telephony (Asterisk/Mango/Beeline/MTS) · staging smoke · **P9 Agent Ops (TZ + CI E2E)** · **v0.16.0 SDK/OpenAPI/restore-drill**.

---

## P8 — Process (BPMN / DMN / CMMN)

_Цель:_ полноценный BPM-модуль на открытых стандартах рядом с PM/CRM; P6e остаётся для простых CRM-правил.  
_ADR:_ [`docs/adr-p8-process.md`](docs/adr-p8-process.md) — SpiffWorkflow + bpmn-js.

### Позиционирование

| Делаем | Не цель (out of scope) |
|--------|-------------------------|
| BPMN 2.0 моделирование + исполнение | Замена Camunda/Signavio «из коробки» |
| DMN таблицы решений + FEEL-lite tables | **Full FEEL** / DMN-стандарт целиком |
| CMMN кейсы (depends_on / required) | **Camunda-grade CMMN** engine |
| Packs ISO 9001/PDCA, ITIL/COBIT, ISO 27001/NIST CSF как шаблоны | Compliance SaaS / сертификация ISO как продукт |
| Mining lite (DFG / bottlenecks) | Celonis-класс discovery / process conformance SaaS |

**Закрыто решением (не бэклог):** Process conformance / full FEEL / Camunda-grade CMMN — не берём в спринты; достаточно P8a–g + FEEL-lite.

### Фазы

- [x] **P8a** — Foundation + BPMN core (definitions, deployments, instances, user tasks, service adapters, inbox, bpmn-js). **L–XL**
- [x] **P8b** — DMN definitions + business-rule tasks. **M**
- [x] **P8c** — Form schema на user tasks + escalation/reminders. **M**
- [x] **P8d** — CMMN case models. **L**
- [x] **P8e** — Compliance process packs (importable XML). **M–L**
- [x] **P8f** — Import/export, миграция P6e → BPMN, process metrics. **S–M**
- [x] **P8 UX** — bpmn-js Modeler, instance token highlight, XOR pack, deep-links Deal/Project. **S–M** (2026-07-23)
- [x] **P8g Advanced** — mining lite (DFG), DMN decisionTable FEEL-lite, richer CMMN (`depends_on`/`available_items`). **M** (2026-07-23)

### Executable BPMN MVP whitelist

Start/End, UserTask, ServiceTask, ExclusiveGateway, ParallelGateway, Timer (Celery), Message start (domain events). Остальное сохраняется в XML, исполнение — later.

---

## P6 — Project CRM

_Цель:_ CRM вокруг проектов и портфеля Fast Plan (B2B услуги/delivery), а не замена Bitrix24/Salesforce «из коробки».  
_Старт:_ 2026-07-22 · _требования заказчика сверены:_ 2026-07-22 · _матрица обновлена:_ **2026-07-28**.

### Снимок: что уже в системе (v0.14.2 + unreleased P9)

**UI (страницы):**

| Путь | Назначение |
|------|------------|
| `/clients` | Организации и контакты (Person), теги, сегменты, timeline, файлы, комментарии |
| `/deals` | Воронка сделок (Kanban), задачи/reminders, click-to-call |
| `/leads` | Лиды, импорт, score, распределение, click-to-call |
| `/crm-tasks` | Единый Kanban задач Deal + Lead (priority, checklist, repeat) |
| `/crm-commerce` | КП/счёт/договор PDF, оплаты, каналы (IMAP/TG), **коннекторы + телефония** |
| `/crm-ai` | AI insights, draft email/КП, summary, suggest tasks |
| `/crm-analytics` | Дашборд, конверсия, LTV/CAC lite, saved reports |
| `/automations` | BPM-lite правила (P6e) |
| `/calendar` | CRM events + Outlook/Google 2-way sync |
| `/agent-ops` | Agent Ops (delivery) — отдельный эпик P9, не CRM-домен |

**Backend (`backend/crm/`):** Organization, Person, Activity, Tag, Segment, Deal (+ pipeline), Lead, DealTask/LeadTask, AutomationRule, ChannelConnection (IMAP/Telegram), Quote/Invoice/Contract + PDF, payments, AR/AP/P&L/cashflow, `crm_role`, IntegrationConnector (Stripe/1C/WA/SMS/telephony), calendar OAuth + sync conflicts, AI endpoints.

**Интеграции и телефония (блок 10):** Calendar OAuth push/pull + conflict policy; IMAP + Telegram → Activity; Stripe / 1C / WhatsApp / SMS webhooks; PBX webhook → `Activity(call)`; outbound dial Asterisk ARI / Mango VPBX / `dial_url`; click-to-call на Person/Deal/Lead; live ARI WebSocket bridge (`run_ari_bridge`).

**Переиспользуется из PM:** Finance, Portfolio, Kanban/WBS, Comments/@mentions, Chats, Audit, Webhooks, API tokens, PWA + offline CRM queue, Web Push, SSO (Microsoft), 2FA/sessions/IP.

### Позиционирование

| Делаем в Fast Plan | Не цель продукта |
|--------------------|------------------|
| Карточка клиента + сделки + задачи в контексте проектов | Маркетинг-автоматизация уровня HubSpot Marketing Hub |
| BPM-lite (P6e) + полноценный BPMN/DMN/CMMN (P8) + AI | Полноценный WMS / встроенный dialer «из коробки» |
| REST + webhooks + OAuth (SSO + calendar) + GraphQL lite + `@fast-plan/crm-client` | Native apps на старте |
| Переиспользование Finance, Calendar, Kanban, Audit, PWA, RBAC | Дублировать отдельный «второй продукт» рядом с PM |

### CRM requirements roadmap — матрица 15 блоков

| # | Требование | В Fast Plan сейчас | Остаток / приоритет |
|---|------------|--------------------|---------------------|
| 1 | MVP: карточка, компании/контакты, история, комменты, файлы, теги, сегменты | **✓ P6b** — `/clients`, API `organizations/people/activities/tags/segments` | — |
| 1b | Сделки: воронка Kanban, стадии, %, сумма, прогноз, задачи, reminders | **✓ P6c** — `/deals`, DealTask | — |
| 1c | Лиды: импорт, распределение, дедуп, score | **✓ P6d** — `/leads` | — |
| 1d | Контакты: phone/email/соцсети/мессенджеры | **✓ P6b** — поля Person + stale filter | — |
| 1e | Календарь CRM + Google/Outlook | **✓** — CRM events на `/calendar`, OAuth 2-way (push/pull, conflict policy) | — |
| 1f | Задачи CRM: чек-листы, repeat, priority, Kanban | **✓** — DealTask + LeadTask + `/crm-tasks` | — |
| 2 | Автоматизация (BPM / n8n-like) | **✓ P6e** + **P8** BPMN/DMN/CMMN для сложных процессов | — |
| 3 | AI CRM-помощник | **✓ P6f** — `/crm-ai` (OpenAI / Ollama / heuristics) | — |
| 4 | Омниканал (TG/WA/Email/… → одна лента) | **✓ P6g + IG/VK** — IMAP + Telegram + Instagram/VK → Activity; WA/SMS connectors | — |
| 5 | Продажи: счета/КП/договоры/заказы/оплаты/товары/склад | **✓ P6h** — Quote/Invoice/Contract/Act PDF, payments, AR lite | Склад/SKU — только по явному запросу |
| 6 | Финансы CRM: P&L, дебиторка/кредиторка, cashflow forecast | **✓** — AR/AP + P&L + cashflow на `/crm-commerce` | — |
| 7 | Документы по шаблонам (договор/счёт/акт/КП) | **✓ P6h + Акт** — PDF Quote/Invoice/Contract/Act | — |
| 8 | Аналитика: конверсия, LTV, CAC, источники, конструктор отчётов | **✓ P6i + report builder** — `/crm-analytics` + CSV | — |
| 9 | Роли: admin / sales lead / sales / support / accounting / marketing | **✓** — `crm_role` + accounting/marketing в Settings | workspace owner = admin |
| 10 | Интеграции (Calendar, Gmail, TG, WA, SMS, telephony, Stripe, 1C…) | **✓** — Calendar OAuth 2-way; IMAP/TG/IG/VK; Stripe/1C/WA/SMS; telephony Asterisk/Mango/**Beeline/MTS**/generic | — |
| 11 | API: REST, GraphQL, webhooks, OAuth, SDK | **✓** REST + GraphQL lite + **`@fast-plan/crm-client`** + OpenAPI `/api/schema/` | — |
| 12 | UI: темы, adaptive, search, hotkeys, DnD, saved filters, custom fields | **✓** themes, PWA, search, DnD, CRM hotkeys + saved filters + **custom fields** | — |
| 13 | Collab: comments @, notify, chat, audit, co-edit | **Сильно** — comments, mentions, SSE, chats, audit; CRM comments/files ✓ | Co-edit docs — out of scope |
| 14 | Security: 2FA, SSO, audit, backup, encryption, sessions, IP | **✓ P7 + SSO** + `scripts/backup-db.sh` (opt GPG) | — |
| 15 | Mobile: PWA + offline + push | **✓ P7 Mobile** — Web Push + offline CRM queue | — |

**Итог:** ядро CRM + polish + custom fields / SDK / PBX (**v0.16.0**) **закрыто**. Остаётся склад/SKU только по явному запросу («делаем»); MS Project XML — при образце.

### CRM polish (v0.15.0) — закрыт

| Приоритет | Пункт | Статус |
|-----------|-------|--------|
| **P1** | Hotkeys на CRM-страницах (deals/leads/clients) | **✓** |
| **P2** | Saved filters / представления для CRM lists | **✓** |
| **P2** | PDF-шаблон **Акта** | **✓** |
| **P2** | Instagram / VK → Activity | **✓** |
| **P2** | Расширенный report builder | **✓** |
| **P3** | GraphQL read API lite | **✓** |
| **P3** | Backup/encryption hardening (`scripts/backup-db.sh`) | **✓** |
| **P2** | Custom fields на карточках (блок 12) | **✓** v0.16.0 |
| **P3** | Typed CRM SDK (`packages/crm-client`) | **✓** v0.16.0 |
| _запрос_ | Склад / SKU / inventory | только при явном запросе |
| _out_ | Marketing journeys, co-edit docs, native apps | не планируем |

### Что было «доделать» (архив таблицы)

| Приоритет | Пункт | Блок | Оценка |
|-----------|-------|------|--------|
| ~~P1~~ | ~~Hotkeys~~ | 12 | done |
| ~~P2~~ | ~~Saved filters / Акт / IG-VK / report builder~~ | — | done |
| ~~P3~~ | ~~GraphQL lite / backup script~~ | — | done |
| _запрос_ | Склад / SKU / inventory | 5 | **L** — только при явном запросе |
| _out_ | Marketing journeys, co-edit docs, native apps | — | не планируем |

### Уже переиспользуем (не строить заново)

- Finance (`Transaction`, budget, FX), Portfolio  
- Calendar + ICS + CRM events + Outlook/Google push  
- Kanban / WBS / My Tasks / Capacity  
- Comments + @mentions + attachments (work items + CRM)  
- Chats (project/workspace/DM) + guest share  
- Outbound webhooks + API tokens + Audit log  
- Theme light/dark/system, PWA, global search  
- AI drafts pipeline (OpenAI/Ollama) — CRM prompts в P6f  
- Process engine (P8) рядом с P6e automations  

### Фазы реализации

- [x] **P6a Foundation** — `Organization` + `Person` + `Activity`, API, «Клиенты», `Project.client_organization`, Stakeholder→Person, import legacy. **L**
- [x] **P6b Карточка клиента (MVP CRM)** — мессенджеры/соцсети на Person; теги + сегменты; комментарии и файлы на org/person; ответственный менеджер; enrichment timeline (invoice/order kinds); CRM-роли (sales); фильтры stale/tag/segment; «давно не контактировали». **L**
- [x] **P6c Сделки** — Deal + pipeline stages (Kanban), amount/probability/close_date, задачи, задачи/reminders по сделке, связь Deal↔Project/Organization, counterparty в Finance. **L**
- [x] **P6d Лиды** — Lead entity, CSV/API import, assignment round-robin/manual, dedupe (email/phone), lead score (rules). **M–L**
- [x] **P6e Автоматизация (BPM-lite)** — declarative rules trigger→conditions→actions; templates «лид из формы» / «follow-up +2 дня»; delay via deferred queue. **L**
- [x] **P6f AI CRM** — ассистент: «клиенты без покупок», «сделки под риском»; draft email/КП; резюме активности/переписки; auto-tasks; прогноз (поверх P6c данных). **L**
- [x] **P6g Омниканал (этап 1)** — единая лента Activity из Email (Gmail/IMAP) + Telegram bot; WhatsApp/Instagram/VK/телефония — отдельные коннекторы после adoption. **L**
- [x] **P6h Коммерция и документы** — Quote/Invoice/Contract templates → PDF; заказы/оплаты; AR/AP lite + cashflow forecast; **склад/SKU — только если явный запрос** (иначе out of scope). **L**
- [x] **P6i CRM-аналитика** — дашборд: продажи по менеджерам, конверсия, средний чек, источники; LTV/CAC при наличии затрат на лиды; конструктор отчётов (простые saved queries). **M–L**
- [x] **P6 calendar sync** — CRM events на workspace calendar + OAuth push в Outlook/Google (2026-07-25). **M**

### CRM backlog (после P6i) — закрыт

- [x] **CRM tasks UX** — чек-листы, repeat, priority, единый Kanban Deal/Lead tasks (**1f**). **M**
- [x] **CRM finance deep** — P&L по клиенту/сделке, AP, cashflow forecast UI (**6**). **M–L**
- [x] **CRM roles expand** — accounting / marketing поверх `crm_role` (**9**). **S**
- [x] **Connectors on demand** — Stripe, 1С, WhatsApp, SMS, telephony (**10**). **по запросу**
- [x] **Calendar 2-way** — pull + conflict policy (**1e**). **M**
- [x] **Telephony deep** — click-to-call (Person/Deal/Lead), Asterisk AMI/ARI, Mango sign, ARI live bridge (**10**). **M**

### Принцип приоритизации спринтов (CRM)

1. ~~**CRM backlog**~~ — 1f / 6 / 9 / 10 / 1e 2-way / telephony закрыты.
2. ~~**CRM polish + релиз v0.15.0**~~ — Agent Ops + polish закрыты.
3. ~~**Custom fields / SDK / Agent Ops E2E / PBX Beeline·MTS**~~ — **v0.16.0**.
4. MS Project XML import — при наличии образца.
5. Склад / SKU — только по явному запросу («делаем»).
6. Ops hygiene — quarterly `scripts/restore-drill.sh` on staging.

### P6a — критерии (архив)

- [x] CRUD организаций и людей  
- [x] Activity timeline (call / meeting / email / note)  
- [x] Навигация «Клиенты» + поиск  
- [x] `Project.client_organization`  
- [x] Stakeholder → Person  
- [x] Import Contact/Stakeholder (`sync_crm_legacy` / `POST /api/crm/import-legacy/`)

### P6b — критерии готовности ✓

- [x] Поля связи: telegram / whatsapp / social URLs на Person  
- [x] Tags + Segments (правила или ручные списки)  
- [x] Comments + file attachments на Organization/Person  
- [x] `owner` (ответственный менеджер) на Organization/Person (Deal — в P6c)  
- [x] Activity kinds: invoice / order (+ существующие call/email/meeting/note)  
- [x] Workspace CRM roles (sales_lead / sales / support) поверх owner/editor/viewer  
- [x] UI карточки: компания | контакты | история | документы | заметки | менеджер  
- [x] Сигнал «нет касаний N дней»

### P6c — критерии готовности ✓

- [x] Deal entity + pipeline stages (Kanban)  
- [x] amount / probability / close_date + forecast  
- [x] задачи/reminders по сделке  
- [x] Deal ↔ Project / Organization  
- [x] counterparty в Finance (prep)

### P6d — критерии готовности ✓

- [x] Lead entity + CSV/API import  
- [x] Assignment (manual / round-robin)  
- [x] Dedupe email/phone  
- [x] Lead score (rules)

### P6e — критерии готовности ✓

- [x] Trigger → conditions → actions конструктор (declarative JSON rules + UI)
- [x] Actions: create lead/deal/task, assign, webhook, delay
- [x] Шаблоны follow-up / form lead
- [x] Визуальный редактор conditions/actions (вместо сырого JSON)
- [x] Trigger `schedule.daily` + шаблон stale deals

### P6f — критерии готовности ✓

- [x] AI insights: stale clients / at-risk deals
- [x] Draft email / КП
- [x] Activity summary + auto-tasks

### P6g — критерии готовности ✓

- [x] ChannelConnection (IMAP / Telegram)
- [x] Ingest → Activity (channel/direction/external_id) + dedupe
- [x] Celery sync + Telegram webhook
- [x] UI каналов на странице «Коммерция»

### P6h — критерии готовности ✓

- [x] Quote / Invoice / Contract + PDF
- [x] Payments → status paid
- [x] AR lite summary

### P6i — критерии готовности ✓

- [x] Dashboard: conversion, avg check, by owner, by source
- [x] LTV/CAC lite
- [x] Saved report snapshots

### Связанные эпики (не только CRM)

- [x] **P7 Security MVP** — TOTP 2FA, session management, optional IP allowlist, [`SECURITY.md`](SECURITY.md) backup runbook (2026-07-22).
- [x] **P7 Security SSO** — Microsoft OAuth login (Google login временно disabled); calendar OAuth Google/Outlook отдельно (2026-07-23…25).
- [x] **P7 Mobile** — PWA Web Push (VAPID) + offline queue для CRM activities/deal tasks (2026-07-22). **M**
- [x] **Redis pub/sub для SSE** — multi-worker realtime (2026-07-22). **M**
- [x] **P8 Process** — BPMN/DMN/CMMN + P8g mining/DMN tables/richer CMMN (2026-07-23). **XL**

### Вне scope / партнёрский слой (явно)

- Полноценный WMS и складская логистика (**склад/SKU** — только по явному запросу)  
- Встроенная IP-телефония / dialer «как продукт» (коннекторы Asterisk/Mango/Beeline/MTS — ✓)  
- Marketing automation (email journeys, landing builders)  
- Process conformance / **full FEEL** / **Camunda-grade CMMN** (см. P8)  
- Нативные iOS/Android (достаточно усиленного PWA)  
- Co-edit документов уровня Google Docs  

~~Ранее «позже»:~~ GraphQL lite + `@fast-plan/crm-client` + OpenAPI — сделано.

---

## P9 — Agent Ops (мультиагентное исполнение)

_Цель:_ операционный слой исполнения для людей и агентов (ТЗ CryptoGamp ops) — задачи, спринты, handoff, GitHub-связи — **без** превращения Fast Plan в канон документации или крипто-домен.  
_Границы:_ CryptoGamp/любой repo = канон; Fast Plan = исполнение; GitHub = код.

### Позиционирование

| Делаем | Не цель |
|--------|---------|
| Epic / Sprint / DeliveryTask + фиксированный ЖЦ | Замена Jira Cloud «из коробки» |
| Роли агентов + handoff + claim API | Автономное изменение смысла задачи без Owner |
| Ссылки на docs + GitHub branch/PR/checks | Хранение канона / payout / USDC внутри FP |
| Feature flag `agent_ops_enabled` | Ломать существующий Kanban/WBS/CRM |

### Фазы

- [x] **P9a** — Foundation: settings flag, Epic, Sprint, DeliveryTask, SubTask, status history, Blocker, backlog/sprint UI. **L**
- [x] **P9b** — Agent profiles/roles, ACL, structured Handoff, atomic claim. **L**
- [x] **P9c** — GitHub fields + webhook PR status; Ready-gate (doc links / DoR). **M–L**
- [x] **P9d** — Agent API: filters, Idempotency-Key, rate limit, service-account friendly queues. **M**
- [x] **P9e** — TZ end-to-end: full Ready-gate §8, dependencies, field/access journals, service accounts, project meta, review notes/PR snippet, overview+task card UI. **L**
- [x] **P9f** — TZ gap-close: ACL `can()`, assign API, unified timeline, dep gates, SubTask CRUD, comment kinds, project §5.1 list, webhook HMAC, richer Agent Ops UI. **M**
- [x] **P9g** — Ideal TZ close: Owner/Planner meaning-approve queue; universal access log; GitHub branch auto-link + structured reviews + attach-PR PAT; create Project+meta from Agent Ops. **M**
- [x] **P9h** — TZ polish: multi-PR links, Checks webhook, auto-attach, reviews/settings UI, role field ACL, timeline `created`. **M**

### DoD (§17 ТЗ) — выполнен

Проект → эпик → спринт → задача с обязательными полями → назначение роли/исполнителя → статусы → handoff → блокер → links docs/GitHub → история → фильтр очереди по агенту.

### Опционально после TZ

- [x] E2E Playwright сценарии Agent Ops (claim → handoff → meaning approve) — CI `E2E_AGENT_OPS=1`
- [x] Staging smoke для `delivery/` endpoints
- [x] UI polish / onboarding агентов + [`docs/AGENT_OPS.md`](docs/AGENT_OPS.md)

---

## P5 — Чаты (проекты и портфель)

_Выполнено (2026-07-20)._

- [x] Project chat (`ProjectMember` / workspace fallback) и portfolio = workspace chat
- [x] Модерация: `open` / `disabled` / `announcements` + персональный mute
- [x] Сообщения, вложения, пересылка между доступными rooms
- [x] UI: вкладка «Чат», чат портфеля, SSE `chat.message`, уведомления `chat`
- [x] API app `chats` — см. [`backend/chats/`](backend/chats/)
- [x] DM 1:1, треды/ответы, реакции, голосовые
- [x] Гостевой чат через share-link (`allow_chat`, `chat_can_post`)
- [x] Редактирование/удаление сообщений (автор + модератор)
- [x] Авто-архивация отключённых чатов (Celery `chats.archive_disabled_rooms`)

### Цель (архив)

Командная переписка в контексте проекта и на уровне портфеля (workspace).

### Вне scope (остаётся)

- Видеозвонки
- Hardware key / WebAuthn wrapping for recovery

_Выполнено дополнительно:_
- [x] Реакции с emoji-picker / GIF (allowlist giphy/tenor)
- [x] End-to-end шифрование текста DM (ECDH P-256 + AES-GCM, ключи на клиенте)
- [x] Multi-device E2E key sync / recovery phrase (Settings)
- [x] Шифрование вложений и голосовых в DM

При реализации заметной фичи — поднимать версию (PATCH/MINOR) по правилу в `VERSION` / `CHANGELOG.md`.
