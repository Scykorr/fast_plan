# Changelog

Все заметные изменения продукта **Fast Plan** фиксируются в этом файле.

Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/),
версии — [Semantic Versioning](https://semver.org/lang/ru/):

- **MAJOR** — несовместимые изменения API/поведения
- **MINOR** — новая функциональность без ломающих изменений
- **PATCH** — исправления и мелкие улучшения

Источник истины версии: файл [`VERSION`](VERSION) в корне репозитория.
При релизе обновляйте `VERSION`, этот файл, `frontend/package.json` и убедитесь,
что `GET /api/health/` отдаёт ту же версию.

## [Unreleased]

### Added

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

### Planned

См. [ROADMAP.md](ROADMAP.md) — приоритетный бэклог улучшений.

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
