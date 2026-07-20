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

_В работе (2026-07-20): backend API-скaffold; миграции, тесты и UI — следующий спринт._

- [x] **Импорт CSV** — WBS (`POST /api/projects/<id>/import/`) и транзакции (`POST /api/finance/transactions/import/`), те же колонки что у экспорта. **M** _(backend)_
- [ ] **Импорт MS Project / Jira** — отложено, пока нет подтверждённого формата. **L**
- [x] **PERT / сетевой график** — `GET /api/projects/<id>/pert/` (узлы с O/M/P, рёбра FS, критический путь из CPM). **M** _(backend)_
- [x] **Гостевой статус-отчёт** — `ProjectShareLink`, `GET /api/share/<token>/` без авторизации, CRUD ссылок для editor+. **M** _(backend)_
- [x] **AI-черновики** — `POST /api/projects/<id>/ai-draft/` (risks/charter, OpenAI или эвристика). **M** _(backend)_
- [x] **Per-project roles** — `ProjectMember` (manager/contributor/viewer) + `has_project_min_role`. **M** _(backend)_
- [ ] **Мультивалютность и курсы** — модель `ExchangeRate`, поле `Workspace.currency`; API/UI конвертации — не готово. **M**
- [ ] **Frontend P4** — импорт CSV, публичная страница `/share/:token`, PERT-диаграмма, управление share links и project members. **L**
- [ ] **Тесты и релиз v0.9.0** — миграции, pytest, UI smoke, CHANGELOG. **M**

---

## Как выбирать следующий спринт

Рекомендуемый порядок «максимум пользы / минимум риска» после v0.8.0:

1. **Завершить P4 backend** — миграции для `ProjectShareLink`, `ProjectMember`, `ExchangeRate`; pytest на import/share/pert/ai-draft.
2. **Frontend по приоритету продукта** — CSV import → guest `/share/:token` → PERT рядом с Gantt/CPM.
3. **Мультивалюта** — API курсов + конвертация в Finance/Portfolio (если нужна до v0.9.0).
4. Параллельно на staging: SMTP verification, webhook delivery, PWA install/update (P3 hardening).

При реализации заметной фичи — поднимать версию (PATCH/MINOR) по правилу в `VERSION` / `CHANGELOG.md`.
