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

1. **MS Project XML import** — при появлении подтверждённого формата/образца.
2. ~~**Чаты проектов и портфеля**~~ — см. P5 (выполнено).
3. **Redis pub/sub для SSE** — надёжные realtime-события при multi-worker gunicorn (сейчас E2E soft-fallback).
4. **P6 Project CRM** — P6a–P6f ✓; следующий: **P6g** (омниканал) или P6i по запросу.

---

## P6 — Project CRM

_Цель:_ CRM вокруг проектов и портфеля Fast Plan (B2B услуги/delivery), а не замена Bitrix24/Salesforce «из коробки».  
_Старт:_ 2026-07-22 · _требования заказчика сверены:_ 2026-07-22.

### Позиционирование

| Делаем в Fast Plan | Не цель продукта |
|--------------------|------------------|
| Карточка клиента + сделки + задачи в контексте проектов | Маркетинг-автоматизация уровня HubSpot Marketing Hub |
| Встроенный BPM-lite + AI поверх уже существующих AI-черновиков | Полноценный WMS / телефония / мессенджер-шлюз «всё сразу» |
| REST + webhooks + OAuth-интеграции точечно | GraphQL + SDK + native apps на старте |
| Переиспользование Finance, Calendar, Kanban, Audit, PWA, RBAC | Дублировать отдельный «второй продукт» рядом с PM |

### Матрица требований (15 блоков) → статус

| # | Требование | В Fast Plan сейчас | Приоритет в P6 |
|---|------------|--------------------|----------------|
| 1 | MVP: карточка, компании/контакты, история, комменты, файлы, теги, сегменты | **P6b ✓** — карточка + теги/сегменты/комменты/файлы/мессенджеры | **P6b** |
| 1b | Сделки: воронка Kanban, стадии, %, сумма, прогноз, задачи, reminders | **P6c ✓** — Deal + pipeline + forecast + DealTask reminders | **P6c** |
| 1c | Лиды: импорт, распределение, дедуп, score | **P6d ✓** — Lead + CSV/API import, RR/manual, dedupe, rules score | **P6d** |
| 1d | Контакты: phone/email/соцсети/мессенджеры | **P6b ✓** — telegram/whatsapp/social_urls | **P6b** |
| 1e | Календарь CRM + Google/Outlook | **Частично** — workspace calendar/ICS; нет CRM-сущностей и OAuth-sync | **P6b** + интеграции |
| 1f | Задачи CRM: чек-листы, repeat, priority, Kanban | **Частично** — WBS/Kanban/My Tasks; не привязаны к Deal/Lead | **P6c** |
| 2 | Автоматизация (BPM / n8n-like) | **P6e ✓** — AutomationRule + templates + delay queue | **P6e** |
| 3 | AI CRM-помощник (резюме звонков, риски сделок, письма, КП) | **✓ P6f** — insights, draft email/КП, summary, suggest tasks | — |
| 4 | Омниканал (TG/WA/Email/… → одна лента) | **Нет** (есть внутренние чаты + guest chat) | **P6g** (этапами) |
| 5 | Продажи: счета/КП/договоры/заказы/оплаты/товары/склад | **Частично** — Finance transactions; нет КП/договоров/SKU/склада | **P6h** (без полноценного склада) |
| 6 | Финансы CRM: P&L, дебиторка/кредиторка, cashflow forecast | **Частично** — доходы/расходы/бюджет проекта; нет AR/AP/forecast | **P6h** + Finance |
| 7 | Документы по шаблонам (договор/счёт/акт/КП) | **Частично** — PDF status report | **P6h** |
| 8 | Аналитика: конверсия, LTV, CAC, источники, конструктор отчётов | **Частично** — portfolio/burndown/velocity/EVM | **P6i** |
| 9 | Роли: admin / sales lead / sales / support / accounting / marketing | **Частично** — P6b: `crm_role` (sales_lead/sales/support) на WorkspaceMember | **P6b** + later |
| 10 | Интеграции (Calendar, Gmail, TG, WA, SMS, telephony, Stripe, 1C…) | **Частично** — webhooks, API tokens | точечно в **P6e/g/h** |
| 11 | API: REST, GraphQL, webhooks, OAuth, SDK | **Частично** — REST + JWT + webhooks + API tokens | REST/OAuth **P6e**; GraphQL/SDK — позже / вне MVP |
| 12 | UI: темы, adaptive, search, hotkeys, DnD, saved filters, custom fields | **Сильно** — themes, PWA, search, DnD Kanban/WBS, custom fields tracking | доработка CRM UI в **P6b+** |
| 13 | Collab: comments @, notify, chat, audit, co-edit | **Сильно** — comments, mentions, SSE, chats, audit; CRM comments/files в **P6b ✓** | **P6b** |
| 14 | Security: 2FA, SSO, audit, backup, encryption, sessions, IP allowlist | **Частично** — audit, chat E2E, JWT/CSRF; нет 2FA/SSO/IP | **P7 Security** (см. ниже) |
| 15 | Mobile: PWA + offline + push | **Частично** — PWA shell/offline; нет push | **P7 Mobile** |

### Уже переиспользуем (не строить заново)

- Finance (`Transaction`, budget, FX), Portfolio, Calendar + ICS  
- Kanban / WBS / My Tasks / Capacity  
- Comments + @mentions + attachments (work items)  
- Chats (project/workspace/DM) + guest share  
- Outbound webhooks + API tokens + Audit log  
- Theme light/dark/system, PWA, global search  
- AI drafts pipeline (OpenAI/Ollama) — расширять на CRM-промпты  

### Фазы реализации

- [x] **P6a Foundation** — `Organization` + `Person` + `Activity`, API, «Клиенты», `Project.client_organization`, Stakeholder→Person, import legacy. **L**
- [x] **P6b Карточка клиента (MVP CRM)** — мессенджеры/соцсети на Person; теги + сегменты; комментарии и файлы на org/person; ответственный менеджер; enrichment timeline (invoice/order kinds); CRM-роли (sales); фильтры stale/tag/segment; «давно не контактировали». **L**
- [x] **P6c Сделки** — Deal + pipeline stages (Kanban), amount/probability/close_date, задачи, задачи/reminders по сделке, связь Deal↔Project/Organization, counterparty в Finance. **L**
- [x] **P6d Лиды** — Lead entity, CSV/API import, assignment round-robin/manual, dedupe (email/phone), lead score (rules). **M–L**
- [x] **P6e Автоматизация (BPM-lite)** — declarative rules trigger→conditions→actions; templates «лид из формы» / «follow-up +2 дня»; delay via deferred queue. **L**
- [x] **P6f AI CRM** — ассистент: «клиенты без покупок», «сделки под риском»; draft email/КП; резюме активности/переписки; auto-tasks; прогноз (поверх P6c данных). **L**
- [ ] **P6g Омниканал (этап 1)** — единая лента Activity из Email (Gmail/IMAP) + Telegram bot; WhatsApp/Instagram/VK/телефония — отдельные коннекторы после adoption. **L**
- [ ] **P6h Коммерция и документы** — Quote/Invoice/Contract templates → PDF; заказы/оплаты; AR/AP lite + cashflow forecast; **склад/SKU — только если явный запрос** (иначе out of scope). **L**
- [ ] **P6i CRM-аналитика** — дашборд: продажи по менеджерам, конверсия, средний чек, источники; LTV/CAC при наличии затрат на лиды; конструктор отчётов (простые saved queries). **M–L**

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

### Связанные эпики (не только CRM)

- [ ] **P7 Security** — 2FA, SSO (Google/Microsoft), session management, optional IP allowlist, backup runbook. **L**
- [ ] **P7 Mobile** — PWA push notifications, offline queue для CRM activities/tasks. **M**
- [ ] **Redis pub/sub для SSE** — для realtime CRM/чат при multi-worker. **M**

### Вне scope / партнёрский слой (явно)

- Полноценный WMS и складская логистика  
- Встроенная IP-телефония / dialer (интеграция через коннектор)  
- Marketing automation (email journeys, landing builders)  
- GraphQL + официальный SDK — после стабилизации REST  
- Нативные iOS/Android (достаточно усиленного PWA)  
- Co-edit документов уровня Google Docs  

### Принцип приоритизации спринтов

1. **P6g** — омниканал (по запросу) или **P6i** аналитика.
2. 1С/Stripe — по запросу клиентов, не блокеры MVP.

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
