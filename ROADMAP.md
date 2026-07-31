# Roadmap Fast Plan

Живой документ продукта.  
**Сейчас читайте сверху вниз:** статус → что уже есть → что планируем → вне scope.  
Детали прошлых эпиков и хронология релизов — в [архиве](#архив) в конце.

При реализации пункта: запись в [`CHANGELOG.md`](CHANGELOG.md) → `[Unreleased]`, затем отметить здесь ✓ и перенести в **Сделано**.  
Оценка: **S** — часы/день · **M** — несколько дней · **L** — неделя+.

---

## Статус

| | |
|---|---|
| **Текущая версия** | **v0.18.0** ([`VERSION`](VERSION), [`CHANGELOG.md`](CHANGELOG.md)) |
| **Ядро продукта** | PM + CRM + Process + Agent Ops + Security/PWA — **закрыто** |
| **Следующий слой** | [Планы](#планы--что-делаем-дальше) — MS Project (sample) / leveling / Inclusive GW |
| **Блокер** | MS Project XML — нужен sample `.xml` / `.mpp` |

---

## Сделано — что уже в продукте

Кратко по доменам. Всё ниже **уже в коде** (на момент v0.18.0).

### Управление проектами (PM)

| Область | Что есть | Где |
|---------|----------|-----|
| Структура | WBS, Gantt, шаблоны, RACI, риски, stakeholders, charter | `/projects/:id` |
| Исполнение | Kanban ↔ WBS, «Мои задачи», time entries, capacity + overload hints | `/kanban`, `/tasks`, `/capacity`, Gantt/WBS |
| Сроки / аналитика | PERT/сеть + **P10/P50/P90 finish**, CPM/EVM, baselines, **change requests**, burndown | вкладки проекта |
| Портфель | сводка SPI/CPI/FX + **cross-project deps** (activity picker) | `/portfolio` |
| Обмен | CSV/XLSX/ICS, Jira CSV import, guest status share | проект / `/share/:token` |
| AI | черновики WBS/risks/charter, refine, Ollama/OpenAI | проект |
| Handoff | Deal → Project from template | `/deals`, `POST …/create-project/` |

### Управление процессами (Process)

| Область | Что есть | Где |
|---------|----------|-----|
| BPMN | bpmn-js + Spiff whitelist; timers; Inclusive experimental (catalog) | `/processes` |
| Adapters | catalog ServiceTask ops (+ `create_wbs_note`) | `GET /process/adapters/`, вкладка Adapters |
| DMN / CMMN | FEEL-lite; CMMN lite (`depends_on`) | `/processes` |
| Ops | inbox, metrics, mining lite, **stuck/aging/SLA** | `/process-tasks`, вкладка Ops |
| BPMN SubProcess | embedded SubProcess + **child ProcessInstance** mirror | engine + instance list |
| Связка | UserTask ↔ WBS/Kanban; CRM events → start process | `/process-tasks`, automations / category |
| Packs | ISO 9001/PDCA, ITIL/COBIT, ISO 27001 | import packs |
| ADR | SpiffWorkflow + bpmn-js | [`docs/adr-p8-process.md`](docs/adr-p8-process.md) |

### CRM

| Область | Что есть | Где |
|---------|----------|-----|
| Клиенты | Org/Person, теги, сегменты, timeline, **merge/dedupe**, custom fields | `/clients` |
| Продажи | Deal pipeline, Lead, CRM tasks Kanban | `/deals`, `/leads`, `/crm-tasks` |
| Коммерция | КП/счёт/договор/акт PDF, line editor+SKU, оплаты, AR/AP, P&L, cashflow | `/crm-commerce` |
| Договоры | **renewal_date / ARR lite**, upcoming + **remind → DealTask/notify** | `/crm-commerce`, `GET/POST /crm/renewals/` |
| Гостевой портал | КП/счёт/акт: approve + PDF по token | `/commerce/:token` |
| Склад | SKU + movements; списание invoice→paid; **1С pending_skus → SKU** | `/crm-commerce`, `/api/crm/skus/` |
| Склейка | Activity → WBS / process (picker UI) | `/clients` spawn |
| Каналы / PBX / календарь / AI / API | как раньше | commerce, calendar, crm-ai, OpenAPI |

### Платформа и соседние модули

| Область | Что есть |
|---------|----------|
| Коллаб | чаты (project/workspace/DM, E2E DM), comments/@mentions, SSE |
| Security | 2FA, sessions, IP allowlist, Microsoft SSO, audit, backup scripts |
| Mobile | PWA, Web Push, offline CRM queue |
| Agent Ops | Epic/Sprint/DeliveryTask, claim/handoff, GitHub — `/agent-ops` |
| Ops/CI | staging smoke, E2E Playwright, restore-drill, version sync |

### Карта UI (основные маршруты)

| Путь | Назначение |
|------|------------|
| `/` Dashboard | обзор workspace |
| `/portfolio` | портфель + cross-project deps |
| `/projects/:id` | PM: WBS / Gantt / Kanban / PERT / baseline+CR / риски… |
| `/kanban`, `/tasks`, `/capacity` | исполнение и загрузка |
| `/clients`, `/deals`, `/leads`, `/crm-tasks` | CRM ядро |
| `/crm-commerce`, `/commerce/:token` | коммерция / гостевой портал |
| `/crm-ai`, `/crm-analytics` | AI / отчёты |
| `/automations`, `/processes`, `/process-tasks` | правила и BPM |
| `/calendar`, `/agent-ops` | календарь, Agent Ops |
| `/finance`, `/audit`, `/admin`, `/settings` | финансы и админка |

---

## Планы — что делаем дальше

Активный бэклог **после P10**. Только открытые пункты. Приоритет: **P1** → **P2** → **P3**.

### Порядок спринтов (рекомендация)

1. ~~**Release 0.18.0**~~ — **✓** (P10 Unreleased → релиз; GitHub `v0.18.0`)
2. ~~**UX glue**~~ — **✓** renewals remind, spawn pickers, schedule-activity picker
3. ~~**BPMN SubProcess**~~ — **✓** subprocess_specs + child ProcessInstance mirror
4. **MS Project XML** — только после sample `.xml` / `.mpp`
5. Ops: staging migrate `0011`/`0016`/`0017`/`0003_subprocess`; раз в квартал `scripts/restore-drill.sh`

### PM — управление проектами

| Pri | Пункт | Size | Зачем |
|-----|-------|------|-------|
| **P2** | Resource leveling lite (предложить сдвиг при overload hint) | **M** | Hints есть — следующий шаг «что делать» |
| **P3** | PERT Monte Carlo (опция рядом с normal approx) | **M** | Точнее хвосты, чем z-score |
| **P3** | MS Project XML import _(нужен sample)_ | **M–L** | Импорт из MS Project / Project Online |

### Process — управление процессами

| Pri | Пункт | Size | Зачем |
|-----|-------|------|-------|
| **P2** | Inclusive Gateway: first-class условия + UI/docs | **M** | Сейчас experimental / Spiff-only |
| **P3** | Миграция running instances при publish новой версии definition | **L** | Ops для долгих процессов |
| **P3** | SubProcess viewer drill-down (коллапс в bpmn-js) | **M** | Backend lifecycle ✓; UI отложен |

### CRM

| Pri | Пункт | Size | Зачем |
|-----|-------|------|-------|
| **P2** | Guest portal: явный статус оплаты / paid_total для гостя | **S** | Частый вопрос после approve |
| **P3** | Live 1С OData / обмен номенклатурой _(нужен стенд)_ | **L** | Углубление после `pending_skus` |

### Отложено (ждём входных данных)

| Пункт | Условие |
|-------|---------|
| MS Project XML import | образец `.xml` / экспорт из MS Project |
| Углубление конкретного PBX / live 1С | боевой стенд заказчика |
| Full SubProcess UI (коллапс/drill-down в viewer) | P3 в планах Process |

---

## Вне scope (не планируем)

| Не делаем | Почему |
|-----------|--------|
| Полноценный WMS / складская логистика | Есть SKU MVP; WMS — другой продукт |
| Full FEEL / Camunda-grade CMMN / process conformance SaaS | Достаточно P8 + FEEL-lite |
| Marketing journeys / landing builders | Не цель Fast Plan |
| Native iOS/Android | Достаточно усиленного PWA |
| Co-edit документов (Google Docs-класс) | Сложность без ядра ценности |
| Встроенный dialer «как продукт» | Есть PBX-коннекторы |
| Видеозвонки в чатах | Явно вне P5 |

---

## Как работать с этим файлом

1. Смотрите **[Планы](#планы--что-делаем-дальше)** — это единственный активный бэклог.  
2. После релиза — строка в [`CHANGELOG.md`](CHANGELOG.md) и уточнение в **[Сделано](#сделано--что-уже-в-продукте)**.  
3. Не раздувайте scope: новые идеи — сначала сюда (P1–P3), не в код.  
4. История «как дошли» — только в [архиве](#архив) ниже.

---

## Архив

Хронология и детали закрытых эпиков. **Не использовать как бэклог.**

### Релизы (кратко)

| Версия | Когда | Суть |
|--------|-------|------|
| 0.4–0.8 | 2026-07-19 | PM foundation → collab, audit, PWA, templates |
| 0.9–0.11 | 2026-07-20 | CSV/Jira import, PERT, AI drafts, FX, hardening |
| 0.12 | 2026-07-23 | SSO, Process P8, Security/Mobile |
| 0.13–0.14.x | 2026-07-25…26 | CRM calendar 2-way, telephony, finance/roles/tasks |
| 0.15 | 2026-07 | Agent Ops P9 + CRM polish |
| 0.16 | 2026-07-29 | Custom fields, CRM SDK/OpenAPI, PBX Beeline/MTS, restore-drill |
| **0.17** | **2026-07-31** | **SKU/склад MVP**, staging smoke/health polish |
| **0.18** | **2026-07-31** | **P10**: handoff, ops, binding, guest portal, capacity, merge, CR, PERT P10/90, adapters, ARR, spawn, cross-deps, 1C SKU |

### Закрытые эпики (ссылки на код/доки)

| Эпик | Статус | Примечание |
|------|--------|-----------|
| P0–P4 PM core | ✓ | invite/RBAC → portfolio/export/PWA/templates |
| P5 Чаты | ✓ | project/workspace/DM, E2E DM |
| P6 CRM (a–i + backlog) | ✓ | матрица 15 блоков закрыта к v0.17 |
| P7 Security + Mobile | ✓ | 2FA, SSO, push, offline queue |
| P8 Process (a–g) | ✓ | BPMN/DMN/CMMN lite; ADR в `docs/` |
| P9 Agent Ops (a–h) | ✓ | TZ + E2E + docs/AGENT_OPS.md |
| Staging/CI ops | ✓ | smoke, e2e, restore-drill |
| **P10 backlog (sprints 1–5)** | ✓ | релиз **v0.18.0**; MS Project остаётся отложенным |

### P10 — закрытые спринты (справка)

| # | Scope | Commit / note |
|---|-------|---------------|
| 1 | Deal→Project + Process ops | `6accf0e` |
| 2 | UserTask↔WBS + guest commerce | `cbbd2e5` |
| 3 | Capacity hints + Org/Person merge | `475e71f` |
| 4 | Change requests + line editor | `66ff7cf` |
| 5 | PERT P10/90, adapters, ARR, spawn, cross-deps, 1C SKU, CRM→process | `ae4284f` |

### P8 — whitelist executable BPMN (справка)

Start/End, UserTask, ServiceTask, ExclusiveGateway, ParallelGateway, Timer (Celery), Message start, **embedded SubProcess** (child instance mirror). Inclusive — experimental.

### P6 — фазы (все ✓)

P6a Foundation · P6b карточка · P6c сделки · P6d лиды · P6e automations · P6f AI · P6g omnichannel · P6h commerce+SKU · P6i analytics · calendar 2-way · telephony deep · custom fields · SDK.

### Полная хронология «Выполнено» (лог)

| Когда | Что |
|-------|-----|
| 2026-07-19 | P0–P3 PM, релизы v0.4–0.8 |
| 2026-07-20 | P4–P5, FX, staging/AI/Ollama/E2E, чаты |
| 2026-07-22 | Redis SSE, P7 Security/Mobile |
| 2026-07-23 | P8 Process, v0.12 SSO |
| 2026-07-25…26 | CRM calendar, telephony, v0.13–0.14.x |
| 2026-07-27…28 | P9 Agent Ops a–h |
| 2026-07-29 | v0.16 custom fields / SDK / PBX polish |
| 2026-07-31 | v0.17 SKU MVP; **P10 → v0.18.0** |

При реализации заметной фичи — поднимать версию по правилу в `VERSION` / `CHANGELOG.md`.
