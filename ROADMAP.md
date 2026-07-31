# Roadmap Fast Plan

Живой документ продукта.  
**Сейчас читайте сверху вниз:** статус → что уже есть → что планируем → вне scope.  
Детали прошлых эпиков и хронология релизов — в [архиве](#архив) в конце.

При реализации пункта: запись в [`CHANGELOG.md`](CHANGELOG.md) → `[Unreleased]`, затем отметить здесь ✓.  
Оценка: **S** — часы/день · **M** — несколько дней · **L** — неделя+.

---

## Статус

| | |
|---|---|
| **Текущая версия** | **v0.17.0** ([`VERSION`](VERSION), [`CHANGELOG.md`](CHANGELOG.md)); Unreleased: Deal→Project + Process ops |
| **Ядро продукта** | PM + CRM + Process + Agent Ops + Security/PWA — **закрыто** |
| **Следующий слой** | [Планы](#планы--что-делаем-дальше) — sprint 2: UserTask↔WBS + guest portal |
| **Блокер** | MS Project XML — нужен sample `.xml` / `.mpp` |

---

## Сделано — что уже в продукте

Кратко по доменам. Всё ниже **уже в коде** (на момент v0.17.0).

### Управление проектами (PM)

| Область | Что есть | Где |
|---------|----------|-----|
| Структура | WBS, Gantt, шаблоны проектов, RACI, риски, stakeholders, charter | `/projects/:id` |
| Исполнение | Kanban ↔ WBS, «Мои задачи», time entries, capacity | `/kanban`, `/tasks`, `/capacity` |
| Сроки / аналитика | PERT/сеть, CPM/EVM, baselines, burndown/velocity | вкладки проекта |
| Портфель | сводка проектов, SPI/CPI, FX | `/portfolio` |
| Обмен | CSV/XLSX/ICS экспорт, Jira CSV import, guest status share | проект / `/share/:token` |
| AI | черновики WBS/risks/charter, refine, Ollama/OpenAI | проект |

### Управление процессами (Process)

| Область | Что есть | Где |
|---------|----------|-----|
| BPMN | моделирование (bpmn-js) + исполнение Spiff (whitelist) | `/processes` |
| DMN / CMMN | FEEL-lite tables; CMMN lite (`depends_on`) | `/processes` |
| Ops | inbox user tasks, metrics, mining lite (DFG) | `/process-tasks`, Process UI |
| Packs | ISO 9001/PDCA, ITIL/COBIT, ISO 27001 шаблоны | import packs |
| CRM-правила | BPM-lite automations (P6e) рядом с BPMN | `/automations` |
| ADR | SpiffWorkflow + bpmn-js | [`docs/adr-p8-process.md`](docs/adr-p8-process.md) |

### CRM

| Область | Что есть | Где |
|---------|----------|-----|
| Клиенты | Org/Person, теги, сегменты, timeline, файлы, custom fields | `/clients` |
| Продажи | Deal pipeline, Lead, CRM tasks Kanban | `/deals`, `/leads`, `/crm-tasks` |
| Коммерция | КП/счёт/договор/акт PDF, оплаты, AR/AP, P&L, cashflow | `/crm-commerce` |
| Склад | SKU каталог, остатки, списание при invoice→paid | `/crm-commerce`, `/api/crm/skus/` |
| Каналы | IMAP, Telegram, IG/VK → Activity; WA/SMS/Stripe/1C connectors | `/crm-commerce` |
| Телефония | Asterisk / Mango / Beeline / MTS, click-to-call, ARI bridge | CRM карточки |
| Календарь | CRM events + Outlook/Google 2-way | `/calendar` |
| AI / аналитика | insights, drafts, dashboard, report builder | `/crm-ai`, `/crm-analytics` |
| API | REST, GraphQL lite, OpenAPI, `@fast-plan/crm-client` | `/api/schema/`, `/api/docs/` |

### Платформа и соседние модули

| Область | Что есть |
|---------|----------|
| Коллаб | чаты (project/workspace/DM, E2E DM), comments/@mentions, SSE realtime |
| Security | 2FA, sessions, IP allowlist, Microsoft SSO, audit, backup scripts |
| Mobile | PWA, Web Push, offline CRM queue |
| Agent Ops | Epic/Sprint/DeliveryTask, claim/handoff, GitHub links — `/agent-ops` |
| Ops/CI | staging smoke, E2E Playwright, restore-drill, version sync |
| Handoff | Deal → Project from template — `/deals`, `POST /api/crm/deals/<id>/create-project/` |
| Process ops | stuck / aging / SLA — `/processes` вкладка Ops, `GET /api/process/ops/` |

### Карта UI (основные маршруты)

| Путь | Назначение |
|------|------------|
| `/` Dashboard | обзор workspace |
| `/portfolio` | портфель проектов |
| `/projects/:id` | PM: WBS / Gantt / Kanban / PERT / риски… |
| `/kanban`, `/tasks`, `/capacity` | исполнение и загрузка |
| `/clients`, `/deals`, `/leads`, `/crm-tasks` | CRM ядро |
| `/crm-commerce`, `/crm-ai`, `/crm-analytics` | коммерция / AI / отчёты |
| `/automations`, `/processes`, `/process-tasks` | правила и BPM |
| `/calendar`, `/agent-ops` | календарь, Agent Ops |
| `/finance`, `/audit`, `/admin`, `/settings` | финансы и админка |

---

## Планы — что делаем дальше

Активный бэклог после v0.17.0. Приоритет: **P1** → **P2** → **P3**.

### Порядок спринтов (рекомендация)

1. ~~**Deal → Project from template** + **Process ops dashboard**~~ — **✓** (`6accf0e` / Unreleased)
2. **UserTask ↔ WBS/Kanban** + **Guest commercial portal** ← следующий
3. **Capacity-aware schedule hints** + **Org/Person merge**
4. Остальное по таблицам ниже
5. **MS Project XML** — только после sample
6. Ops: раз в квартал `scripts/restore-drill.sh`

### PM — управление проектами

| Pri | Пункт | Size | Статус |
|-----|-------|------|--------|
| **P1** | Deal → Project from template | **M** | **✓** `POST …/create-project/` + UI `/deals` |
| **P1** | Capacity-aware schedule hints на Gantt/WBS | **M** | план |
| **P2** | Change requests + baseline | **M** | план |
| **P2** | PERT probabilistic finish (P10/P50/P90) | **M** | план |
| **P3** | Cross-project / program dependencies | **L** | план |
| **P3** | MS Project XML import _(нужен sample)_ | **M–L** | отложено |

### Process — управление процессами

| Pri | Пункт | Size | Статус |
|-----|-------|------|--------|
| **P1** | UserTask ↔ WBS/Kanban binding | **M** | план |
| **P1** | Process ops dashboard (stuck / aging / SLA) | **S–M** | **✓** `GET /process/ops/` + вкладка Ops |
| **P2** | Service-adapter catalog | **M** | план |
| **P2** | BPMN expansion (SubProcess, Inclusive GW, timers) | **L** | план |
| **P3** | Start process from CRM events | **M** | план |

### CRM

| Pri | Пункт | Size | Зачем |
|-----|-------|------|-------|
| **P1** | Guest commercial portal (КП/счёт/акт, approve, статус оплаты) | **M** | Клиентский край коммерции |
| **P1** | Org/Person merge + dedupe UI | **S–M** | Чистка дублей из каналов |
| **P2** | Contract renewals / ARR lite | **M** | Retention services |
| **P2** | Quote/Invoice line editor + SKU picker | **S–M** | UX поверх SKU MVP |
| **P3** | 1С ↔ SKU sync lite | **M** | RU B2B номенклатура |
| **P3** | Activity → Process task / WBS item (1 клик) | **S** | Склейка доменов в UI |

### Отложено (ждём входных данных)

| Пункт | Условие |
|-------|---------|
| MS Project XML import | образец `.xml` / экспорт из MS Project |
| Углубление конкретного PBX/1С | боевой стенд заказчика |

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
2. После релиза — строка в [`CHANGELOG.md`](CHANGELOG.md) и перенос пункта в **[Сделано](#сделано--что-уже-в-продукте)**.  
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

### Закрытые эпики (ссылки на код/доки)

| Эпик | Статус | Примечание |
|------|--------|------------|
| P0–P4 PM core | ✓ | invite/RBAC → portfolio/export/PWA/templates |
| P5 Чаты | ✓ | project/workspace/DM, E2E DM |
| P6 CRM (a–i + backlog) | ✓ | матрица 15 блоков закрыта к v0.17 |
| P7 Security + Mobile | ✓ | 2FA, SSO, push, offline queue |
| P8 Process (a–g) | ✓ | BPMN/DMN/CMMN lite; ADR в `docs/` |
| P9 Agent Ops (a–h) | ✓ | TZ + E2E + docs/AGENT_OPS.md |
| Staging/CI ops | ✓ | smoke, e2e, restore-drill |

### P8 — whitelist executable BPMN (справка)

Start/End, UserTask, ServiceTask, ExclusiveGateway, ParallelGateway, Timer (Celery), Message start. Остальное в XML сохраняется, исполнение — в планах P10 (BPMN expansion).

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
| 2026-07-31 | v0.17 SKU MVP; P10 backlog оформлен |

При реализации заметной фичи — поднимать версию по правилу в `VERSION` / `CHANGELOG.md`.
