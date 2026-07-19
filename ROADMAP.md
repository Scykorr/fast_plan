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

---

## P0 — дыры, мешающие реальному использованию

_Выполнено (2026-07-19 / v0.5.0)._

---

## P1 — ценность из уже написанного API + полировка PM

_Выполнено (2026-07-19 / v0.6.0)._

---

## P2 — коллаборация, отчётность, эксплуатация

- [ ] **Realtime** — SSE или WebSocket: обновления Kanban/WBS/комментариев для других участников workspace. **L**
- [ ] **Вложения файлов** — на карточках и WBS work packages (storage + лимиты + preview). **M**
- [ ] **Учёт фактических трудозатрат** — time entries / logged hours; связать с capacity и EVM (сейчас только plan `hours_per_week` и ручной %). **L**
- [ ] **Портфельный обзор** — сводка по всем проектам workspace (SPI/CPI, просрочки, бюджет) одной страницей. **M**
- [ ] **Экспорт** — CSV/XLSX транзакций и WBS; опционально ICS для вех/дедлайнов. **M**
- [ ] **Observability** — structured `LOGGING`, Sentry (backend + frontend), базовые метрики запросов. **S**
- [ ] **Audit log** — неизменяемая история изменений ролей, WBS, финансов (поверх decision-comments). **M**
- [ ] **Фоновые задачи** — переход scheduler → Celery/Redis (retry, очереди) или явный lock + healthcheck для текущего loop. **M**

---

## P3 — продукт «на вырост»

- [ ] **Email verification** при регистрации + редактирование профиля (имя, аватар). **M**
- [ ] **Интеграции** — webhooks исходящие; опционально Slack/Telegram на дедлайны и риски. **L**
- [ ] **API tokens** для внешних клиентов (machine-to-machine) с scope по workspace. **M**
- [ ] **i18n** — вынести строки (`ru` по умолчанию, каркас `en`); валюта не только `₽`. **L**
- [ ] **Тёмная тёплая тема** — рядом с текущей light warm palette. **M**
- [ ] **PWA / offline-friendly** shell для мобильного просмотра задач и уведомлений. **L**
- [ ] **Burndown / velocity** по Kanban-колонкам или sprint-окнам (если введём итерации). **M**
- [ ] **Шаблоны проектов** — создать проект из типового WBS/трекеров. **M**

---

## P4 — идеи на потом (не коммитить без запроса)

- Импорт из MS Project / Jira / CSV.
- Диаграмма сетевого графика (PERT) рядом с CPM.
- Мультивалютность и курсы.
- Гостевой доступ по публичной read-only ссылке на статус-отчёт.
- AI-ассистент: черновик рисков/устава из описания проекта.
- Fine-grained permissions (per-project roles сверх workspace RBAC).

---

## Как выбирать следующий спринт

Рекомендуемый порядок «максимум пользы / минимум риска» после v0.6.0:

1. По запросу: realtime, time tracking или observability (P2).
2. Дальше — по мере роста продукта: P3/P4 из бэклога выше.

При реализации заметной фичи — поднимать версию (PATCH/MINOR) по правилу в `VERSION` / `CHANGELOG.md`.
