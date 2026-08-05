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
| **Текущая версия** | **v0.22.0** ([`VERSION`](VERSION), [`CHANGELOG.md`](CHANGELOG.md)) |
| **Ядро продукта** | PM + CRM + Process + Agent Ops + Security/PWA — **закрыто** |
| **Следующий слой** | Ops SMTP verification; S3 Integrations **в перспективе** |
| **В перспективе** | S3 Integrations (MS Project XML + 1С OData) — без sample в ближайшее время |

---

## Сделано — что уже в продукте

Кратко по доменам. Всё ниже **уже в коде** (на момент v0.18.0).

### Управление проектами (PM)

| Область | Что есть | Где |
|---------|----------|-----|
| Структура | WBS, Gantt, шаблоны, RACI, риски, stakeholders, charter | `/projects/:id` |
| Исполнение | Kanban ↔ WBS, «Мои задачи», time entries, capacity + overload hints + **leveling propose** | `/kanban`, `/tasks`, `/capacity`, Gantt |
| Сроки / аналитика | PERT/сеть + **P10/P50/P90 finish**, CPM/EVM, baselines, **change requests**, burndown | вкладки проекта |
| Портфель | сводка SPI/CPI/FX + **cross-project deps** (activity picker) | `/portfolio` |
| Обмен | CSV/XLSX/ICS, Jira CSV import, guest status share | проект / `/share/:token` |
| AI | черновики WBS/risks/charter, refine, Ollama/OpenAI | проект |
| Handoff | Deal → Project from template | `/deals`, `POST …/create-project/` |

### Управление процессами (Process)

| Область | Что есть | Где |
|---------|----------|-----|
| BPMN | bpmn-js + Spiff; timers; **Inclusive supported** (+ pack `or_inclusive`) | `/processes` |
| Adapters | catalog ServiceTask ops (+ `create_wbs_note`) | `GET /process/adapters/`, вкладка Adapters |
| DMN / CMMN | FEEL-lite; CMMN lite (`depends_on`) | `/processes` |
| Ops | inbox, metrics, mining lite, **stuck/aging/SLA** | `/process-tasks`, вкладка Ops |
| BPMN SubProcess | embedded SubProcess + child ProcessInstance; **list drill-down** | engine + `/processes` instances |
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
| Гостевой портал | КП/счёт/акт: approve + PDF по token; **статус оплаты** | `/commerce/:token` |
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

1. ~~**Release 0.18.0**~~ — **✓**
2. ~~**UX glue**~~ — **✓** renewals / spawn / cross-deps pickers
3. ~~**BPMN SubProcess**~~ — **✓** child ProcessInstance mirror
4. ~~**SMTP tooling + guest payment**~~ — **✓**
5. ~~**Schedule + Process maturity**~~ — **✓** leveling propose, Inclusive GW, SubProcess children UI
6. ~~**SMTP credentials on staging**~~ — **✓ код + локальный SMTP**; staging/prod: test-send → `REQUIRE_EMAIL_VERIFICATION=true` ([`docs/SMTP.md`](docs/SMTP.md))
7. ~~**Release 0.19–0.20**~~ — Process-as-WBS + S6 Kanban/time/attachments
8. ~~**S6 хвост + CRM depth**~~ — **✓** (v0.21.0)
9. ~~**SMTP verification (local)**~~ — **✓** `.env` + test-send; staging/prod: тот же чеклист в STAGING/DEPLOY
10. ~~**Ops: staging migrate backlog + restore-drill**~~ — **✓** STAGING § Migrate backlog / Quarterly restore drill; `restore-drill.sh` + `migrate --check`

### Крупные спринты вперёд (сформированы)

| # | Спринт | Scope | Size | Зависимости |
|---|--------|-------|------|-------------|
| **S1** | **Schedule intelligence** | PERT Monte Carlo; leveling apply-all/undo; Capacity propose | **L** | **✓** |
| **S2** | **Process ops maturity** | migrate on publish; SubProcess collapse; Inclusive tip | **L** | **✓** |
| **S3** | **Integrations unlock** | MS Project XML + 1С OData | **L** | **в перспективе** (нет sample) |
| **S4** | **Trust & mail go-live** | SMTP + verification | **M** | **✓ код**; credentials на staging/prod |
| **S5** | **Process-as-WBS — foundation** | materialize + tree UI | **L** | **✓** |
| **S6** | **Process-as-WBS — PM surface** | dates/RACI/Gantt/Kanban/time/files + comments/capacity/CSV/DnD | **L** | **✓** |
| **S7** | **Methodology + CRM depth** | packs; BANT/playbook + health/Quote→WBS | **L** | **✓ lite** + health/Quote→WBS |

Параллельно: **S4** (ops). После S5–S6 продукт закрывает разрыв «процесс рисуем в BPMN, работаем как в WBS».

---

### Эпик: Process-as-WBS (процесс как дерево работ)

**Идея.** Сейчас процесс = BPMN-граф + inbox UserTask; проект = WBS с Gantt/Kanban/PERT/RACI/capacity. Связка точечная (bind, spawn, `create_wbs_note`).  
**Цель:** у **экземпляра процесса** (и опционально у definition) появляется **иерархическое дерево работ** — тот же UX/функции, что у проектного WBS, но узлы порождаются из BPMN (и обратно синхронизируются).

#### Почему это осмысленно (методологии)

| Методология | Что даёт Process-as-WBS |
|-------------|-------------------------|
| **PMBOK / ISO 21500** | WBS — декомпозиция deliverable; процессные шаги становятся measurable work packages |
| **PRINCE2** | Product-based planning: дерево продуктов/работ рядом с процессом стадии |
| **BPMN 2.0** | Executable flow остаётся источником правды для ветвлений; дерево — *view* для людей и учёта труда |
| **Lean / Value Stream** | Линейная/иерархическая раскладка шагов для lead time, WIP, bottlenecks (поверх mining lite) |
| **ITIL / ISO 9001 packs** | Уже есть BPMN-пакеты — дерево работ делает их «исполняемыми как проект» без ручного bind |
| **Agile / Scrum** | Не замена бэклога; опциональный mapping UserTask → WP → Kanban column (уже частично есть) |

#### Что **не** делаем в эпике

- Не подменяем bpmn-js модельер деревом (граф остаётся для gateways/timers).
- Не строим второй Spiff-engine «на дереве».
- Не обещаем 1:1 Camunda Cockpit / Celonis.

#### Фазы

| Фаза | Scope | Size | Результат |
|------|-------|------|-----------|
| **A. Materialize** | `POST …/instances/<id>/materialize-wbs/` (или auto on start): UserTask/SubProcess/ServiceTask → узлы `ProcessWorkNode` **или** reuse `WBSNode` с `process_instance_id`; иерархия = вложенность SubProcess + document order | **L** | дерево видно в UI |
| **B. Tree UI** | Вкладка «Дерево» на instance: mind-map / list как `WBSTreeView` (ПКМ, rename, focus, collapse); прогресс узла ↔ статус UserTask | **L** | работа без открытия только inbox |
| **C. PM functions** | На дереве процесса: **assignee**, dates → mini-Gantt, **dependencies** (FS из sequenceFlow где однозначно), **RACI**, comments/attachments/time entries, capacity hints | **L** | «все функции WBS» в разумном MVP |
| **D. Sync & templates** | Definition → шаблон дерева; re-materialize при publish (осторожно с running); экспорт CSV/XLSX; AI «уточнить дерево процесса» | **M–L** | шаблоны и обмен |

**Модель (черновик ADR):** либо `ProcessWorkNode` (process-scoped, зеркало полей WBS), либо `WBSNode` + nullable `project` + `process_instance` XOR constraint. Предпочтительнее **отдельная сущность + shared UI kit**, чтобы не ломать project-only инварианты.

**Критерий «все возможные функции» (чеклист MVP C):**

- [x] иерархия + DnD reorder (sibling-only; без reparent BPMN)
- [x] карточка узла (описание, статус, assignee)
- [x] даты / длительность / Gantt-lite
- [x] Kanban-синк для UserTask-узлов
- [x] комментарии / вложения / time log
- [x] RACI на узле
- [x] capacity hint при assignee+dates
- [x] экспорт flatten CSV
- [x] связка «открыть BPMN element» ↔ узел дерева (highlight)

---

### Методологический бэклог (добавить в продукт)

Опираемся на пробелы относительно PMBOK / PRINCE2 / Agile / BPMN / CRM (BANT/MEDDIC lite). Только то, чего **ещё нет** или слабо.

#### PM — управление проектами

| Pri | Пункт | Size | Методология / зачем |
|-----|-------|------|---------------------|
| ~~**P2**~~ | ~~Resource leveling lite~~ | **M** | **✓** |
| ~~**P2**~~ | ~~Leveling apply-all / Capacity propose _(S1)_~~ | **M** | **✓** Capacity apply/undo + Gantt |
| **P3** | PERT Monte Carlo _(S1)_ | **M** | Schedule risk |
| **P3** | MS Project XML _(S3)_ | **M–L** | **в перспективе** |
| **P2** | **OBS / org breakdown** — привязка WBS к оргструктуре (отдел/роль), не только user | **M** | PMBOK org / RACI scale |
| ~~**P2**~~ | ~~**Issue / action log** отдельно от Risk (проблемы + due + owner)~~ | **M** | **✓** PRINCE2 Issue Register (`ProjectIssue`) |
| ~~**P2**~~ | ~~**Lessons learned** на закрытии проекта (шаблон + export)~~ | **S–M** | **✓** `ProjectLessonsLearned` |
| **P3** | **Earned Schedule** (ES/SV(t)) рядом с EVM lite | **M** | Современный EVM |
| **P3** | **Stage / phase gates** на проекте (чеклист go/no-go) | **M** | PRINCE2 stages |
| **P3** | **Quality checklist** на WP (pass/fail + evidence link) | **M** | Quality mgmt |
| **P3** | **Benefit / outcome** поля на deliverable + tracking | **M** | Benefits realization |

#### Process — управление процессами

| Pri | Пункт | Size | Методология / зачем |
|-----|-------|------|---------------------|
| ~~**P2**~~ | ~~Inclusive Gateway~~ | **M** | **✓** |
| **P3** | Instance migration on publish _(S2)_ | **L** | Ops |
| **P3** | SubProcess bpmn-js collapse _(S2)_ | **M** | Usability |
| ~~**P3**~~ | ~~SubProcess list drill-down~~ | **S** | **✓** |
| **P1** | **Process-as-WBS** фазы A–B _(S5)_ | **L** | см. эпик |
| **P1** | **Process-as-WBS** фазы C–D _(S6)_ | **L** | «все функции WBS» |
| ~~**P2**~~ | ~~**SLA timers UI** на UserTask (due из timer/duration) + breach board~~ | **M** | **✓** inbox badges + Ops breach board |
| ~~**P2**~~ | ~~**Process RACI** на definition (роль → lane/candidate)~~ | **M** | **✓** `ProcessDefinitionLaneRole` |
| **P3** | **Value-stream metrics** (cycle/lead time per element) поверх mining | **M** | Lean |
| **P3** | **Compensation / error boundary** lite в catalog + docs | **L** | BPMN advanced |
| **P3** | Pack: **PRINCE2 stage** + **Scrum ceremony** (не сертификация) | **M** | Methodology packs |

#### CRM

| Pri | Пункт | Size | Методология / зачем |
|-----|-------|------|---------------------|
| ~~**P2**~~ | ~~Guest payment status~~ | **S** | **✓** |
| **P3** | Live 1С OData _(S3)_ | **L** | **в перспективе** |
| ~~**P2**~~ | ~~**Qualification score** (BANT)~~ | **M** | **✓** |
| ~~**P2**~~ | ~~**Playbooks** на стадии pipeline~~ | **M** | **✓** |
| ~~**P2**~~ | ~~**Customer health**~~ | **M** | **✓ lite** |
| ~~**P3**~~ | ~~**Quote→WBS estimate**~~ | **M** | **✓ lite** |
| **P3** | **Multi-currency deal rollup** с FX уже в workspace | **S–M** | Finance/CRM |
| **P3** | **Consent / GDPR lite** на Person (legal basis, retention flag) | **M** | Compliance |

### Платформа / Ops

| Pri | Пункт | Size | Зачем |
|-----|-------|------|-------|
| ~~**P1**~~ | ~~**SMTP credentials**~~ | **S–M** | **✓** локально (Yandex); staging/prod — по STAGING.md |
| ~~**P1**~~ | ~~Включить **email verification** после SMTP~~ | **S** | **✓** локально `REQUIRE_EMAIL_VERIFICATION=true` |
| ~~**P2**~~ | ~~UI Settings: SMTP status / test-send~~ | **S** | **✓** |
| ~~**P3**~~ | ~~Deliverability checklist~~ | **S** | **✓** STAGING + docs/SMTP.md |

### Отложено / в перспективе

| Пункт | Условие |
|-------|---------|
| **S3** MS Project XML import | образец `.xml` / `.mpp` — **не ожидается в ближайшее время** |
| **S3** Live 1С OData | боевой стенд заказчика |
| Углубление конкретного PBX | боевой стенд заказчика |
| Full SubProcess UI (коллапс в bpmn-js) | позже при необходимости |
| Camunda-grade conformance / full FEEL | вне scope (см. ниже) |

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
| **0.19–0.21** | **2026-08** | Process-as-WBS, S6, CRM health/Quote→WBS |
| **0.22** | **2026-08-05** | SLA UI, Issue Register, ops hygiene |

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

Start/End, UserTask, ServiceTask, ExclusiveGateway, ParallelGateway, **InclusiveGateway**, Timer (Celery), Message start, **embedded SubProcess** (child instance mirror).

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
