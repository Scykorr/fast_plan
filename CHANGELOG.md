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

### Changed

- Администрирование tracking: inline-формы вместо `window.prompt` для трекеров, статусов, полей и enumerations
- Дашборд — командный центр вместо только приветствия и ДР
- Единый `WorkspaceMixin` и permission-классы в `workspaces/`
- После accept invitation активный workspace переключается автоматически
- GET charter/dashboard/tracking-metadata без лишних side-effect записей для viewer

### Planned

См. [ROADMAP.md](ROADMAP.md) — приоритетный бэклог улучшений.

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
