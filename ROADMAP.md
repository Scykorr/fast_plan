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
- [x] **Тёмная тёплая тема** — рядом с текущей light warm palette. **M**
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

_Выполнено (2026-07-20): staging checklist, AI WBS/schedule, per-project prompts, WBS refine в диалоге, smoke script._

Рекомендуемый порядок после v0.11.0:

1. ~~**MS Project XML import**~~ — отложено до появления образца `.mpp`/XML.
2. ~~**Staging checklist**~~ — [`STAGING.md`](STAGING.md) + `GET /api/health/?extended=1` + `scripts/staging-smoke-check.mjs`.
3. ~~**Расширение AI**~~ — WBS/schedule drafts, `Project.ai_prompts`, итеративное уточнение в диалоге.

Следующие кандидаты:

1. **MS Project XML import** — при появлении подтверждённого формата/образца.
2. **Ollama / локальный LLM** — бесплатная альтернатива OpenAI для AI-черновиков.
3. **Staging smoke в CI** — job с docker-compose и полным прогоном smoke-check.

При реализации заметной фичи — поднимать версию (PATCH/MINOR) по правилу в `VERSION` / `CHANGELOG.md`.
