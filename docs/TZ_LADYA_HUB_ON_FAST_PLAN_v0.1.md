# ТЗ для Cursor: контур «Ладья» на базе Fast Plan

**Версия:** 0.1  
**Дата:** 2026-11-07  
**Продукт-носитель:** [Scykorr/fast_plan](https://github.com/Scykorr/fast_plan) (имя пока не меняем)  
**Заказчик / куратор:** Антон (fedosov)  
**Статус:** поручение на начало разработки модуля, не приёмка Lab-0 и не замена общей «Ладьи»

Скопируй этот файл в корень или `docs/` репозитория `fast_plan` и работай **только** в отдельной ветке.  
Этот документ — инструкция агенту Cursor: что делать, чего не делать, как принять результат.

---

## 0. Одна фраза цели

Сделать в Fast Plan **операционный контур лабораторий Ладьи**: несколько лабораторий могут передавать друг другу **пакеты работы** (задача + файлы + статус + основания), люди пишут во **вход ЛАДа**, а агенты берут работу только через **inbox / handoff** — не через сырой чат.

Философия уже есть в Fast Plan (`docs/CUSTOMER_AGENT_LOOP.md`):  
**чат — диспетчер; доска — передача работы.** Не ломать её.

---

## 1. Где работать

| Параметр | Значение |
| --- | --- |
| Репозиторий | `Scykorr/fast_plan` |
| Базовая ветка | `main` |
| Рабочая ветка | `feature/ladya-hub` (создать от актуального `main`) |
| Стек | Django 6 + DRF + JWT + PostgreSQL; React + TS + Vite + Tailwind |
| Не трогать | `ladya_main_test` (стенды/возвраты лабораторий) — это другой контур |

### Порядок старта (агент)

1. Клонировать/открыть `fast_plan`, `git fetch`, `git checkout main`, `git pull`.
2. `git checkout -b feature/ladya-hub`.
3. Прочитать: `README.md`, `docs/CUSTOMER_AGENT_LOOP.md`, `docs/AGENT_OPS.md`, `backend/chats/models.py`, `backend/delivery/` (Agent Ops), `backend/attachments/`, `backend/workspaces/`.
4. Реализовать **только Milestone M0** из этого ТЗ, затем остановиться и отчитаться.
5. Коммиты — мелкие, осмысленные; не делать release/tag без просьбы человека.

---

## 2. Что уже reuse (не писать заново)

| Возможность | Где в Fast Plan | Как использовать |
| --- | --- | --- |
| Workspace / роли | `workspaces` | Один workspace-тип/флаг «Ladya mode» или отдельные workspace на лабораторию |
| Kanban / WBS / задачи | `kanban`, `projects`, `delivery` | Карточка/DeliveryTask = носитель поручения |
| Handoff агентов | Agent Ops (`delivery`) | Передача исполнителя + журнал |
| Чаты | `chats` (project/workspace/DM, E2E DM) | Человеческое обсуждение; не объект истины по задаче |
| Вложения | `attachments` | Файлы к задаче; для больших — см. ограничения M0 |
| Telegram вход | CRM channels telegram webhook | Позже: сузить до «заявка → пакет»; в M0 не обязателен |
| Auth / 2FA / audit | `accounts`, `audit` | Без ослабления security |

---

## 3. Не цели (явно запрещено в этой ветке)

1. Не переименовывать продукт и репозиторий.
2. Не писать новый мессенджер / не подключать Matrix/Mattermost.
3. Не объявлять Lab-0 развёрнутой и не имитировать приёмку лабораторий.
4. Не тащить в M0 полный CRM/финансы/1С/BPMN — только то, что нужно контуру лабораторий.
5. Не делать автозапуск агентов из чата/Telegram («сообщение = приказ»).
6. Не класть секреты, реальные корпоративные данные, cloud keys.
7. Не ломать существующие тесты Fast Plan; новые фичи — за feature-flag.
8. Не раздувать E2E групповых комнат до «как Signal» в M0 — достаточно модели данных и UI-каркаса.

---

## 4. Продуктовая модель (для реализации)

### 4.1. Сущности

**Laboratory** — логическая площадка внутри workspace (или 1:1 с workspace — выбрать один вариант в ADR и зафиксировать).

Минимальные типы:

- `central_lad` — центральный ЛАД  
- `lab0` — нулевая / методологическая  
- `private_lab` — частная (Никита / Павел / Дмитрий / Антон-стенд и т.п.)  
- `external_intake` — не лаборатория-исполнитель, а очередь входа людей (можно флагом на central_lad)

Поля минимума: `slug`, `title`, `kind`, `workspace` FK, `is_active`, timestamps.

**Package** — единица передачи между лабораториями / от человека.

Поля минимума:

- `id` / публичный номер  
- `title`, `summary`  
- `from_laboratory`, `to_laboratory` (nullable на этапе черновика)  
- `status`: `draft` → `submitted` → `accepted` → `in_progress` → `returned` → `closed` / `rejected`  
- `created_by` (User)  
- `linked_delivery_task` или `linked_card` (nullable, одно из; предпочтительно DeliveryTask если Agent Ops включён)  
- `manifest_sha256` (nullable), `notes_limitations`  
- timestamps + простой audit (кто сменил статус)

**PackageFile**

- FK на Package  
- file / storage key  
- `original_name`, `size`, `sha256`, `content_type`  
- `uploaded_by`, `created_at`

**IntakeRequest** (вход обычного человека → ЛАД)

- текст обращения  
- контакт (email/telegram handle — строка)  
- статус: `new` → `triaged` → `converted` → `closed`  
- optional FK → созданный Package  
- `source`: `web_form` | `manual` (Telegram — позже)

### 4.2. Правила

1. Истина по работе = **Package (+ связанная задача)**, не последнее сообщение в чате.  
2. Смена лаборатории-получателя = явный переход статуса + запись в историю (кто/когда/зачем).  
3. Агент не видит чужой inbox: только задачи на своей service account (как сейчас в Agent Ops).  
4. Человек снаружи не получает доступ ко внутренним комнатам lab0/private.  
5. Большой файл: в M0 достаточно корректного hash + лимита; chunked/S3 можно заложить интерфейсом, реализацию — M1.

---

## 5. Milestone M0 — «скелет контура» (сделать сейчас)

### Backend

1. Django app **`ladya`** (или `ladya_hub`): models выше + admin + миграции.  
2. Feature-flag на workspace: `ladya_hub_enabled` (default `false`).  
3. DRF API под флагом:
   - CRUD Laboratory (owner/editor)  
   - CRUD Package + смена статуса с проверками переходов  
   - upload PackageFile (считать sha256 на сервере)  
   - IntakeRequest: create (auth или отдельный scoped endpoint), triage → convert to Package  
4. Права: только участники workspace; не открывать анонимный upload без лимитов.  
5. Тесты pytest: модели, переходы статусов, изоляция workspace, sha256 файла.

### Frontend

1. Раздел **«Ладья»** в сайдбаре (виден только если `ladya_hub_enabled`).  
2. Страницы минимума:
   - список лабораторий  
   - список пакетов + карточка пакета (статус, файлы, from/to)  
   - простая форма входа (Intake) → создаёт IntakeRequest  
3. Не переписывать весь UI Fast Plan; стиль существующий (Tailwind / текущие компоненты).

### Документация в ветке fast_plan

1. `docs/adr-ladya-hub.md` — решение: Laboratory vs Workspace, связь с DeliveryTask, что reuse.  
2. `docs/LADYA_HUB.md` — как включить флаг, как создать lab, как передать package.  
3. Короткая запись в `CHANGELOG.md` → `[Unreleased]`.

### Definition of Done (M0)

- [ ] Ветка `feature/ladya-hub` существует  
- [ ] Миграции применяются на чистой БД  
- [ ] `pytest` по новому app зелёный; старые тесты не краснеют  
- [ ] FE собирается; раздел Ладья скрыт при выключенном флаге  
- [ ] Можно вручную: включить флаг → создать 2 лаборатории → пакет с файлом (sha256) → сменить статус accepted → закрыть  
- [ ] Можно вручную: IntakeRequest → convert → Package  
- [ ] ADR + README-док на месте  
- [ ] Агент остановился и выдал отчёт: что сделано / что не сделано / как проверить

---

## 6. Milestone M1 — следующий (не делать в первом прогоне)

Только набросок, чтобы не расползтись в M0:

- Chunked upload / S3 / лимиты >> 6 МБ  
- Связка Package ↔ DeliveryTask claim/handoff из UI  
- Telegram bot → IntakeRequest (без автозапуска агентов)  
- Комнаты чата на Laboratory + политика видимости  
- Расширение E2E за пределы DM для lab-rooms  
- Роли Ладьи (ЛАД / Картограф / Квест) как AgentProfile roles  
- Экспорт Package как zip+MANIFEST для возврата в центральный контур

---

## 7. Критерии качества кода

- Следовать существующим паттернам Fast Plan (serializers, permissions, `X-Workspace-Id`).  
- Никаких секретов в git.  
- Имена API: `/api/ladya/...`.  
- Русский UI-копирайт допустим (как в продукте).  
- Комментарии в коде — только где неочевидно; ADR — для решений.  
- Не рефакторить соседние модули «заодно».

---

## 8. Промпт для нового чата Cursor (вставить целиком)

```text
Работаем в репозитории Scykorr/fast_plan.
Ветка: создай и используй feature/ladya-hub от актуального main.

Прочитай и выполни ТЗ: docs/TZ_LADYA_HUB_ON_FAST_PLAN_v0.1.md
(если файла ещё нет — он будет добавлен / вставлен в docs/).

Сделай ТОЛЬКО Milestone M0. Не делай M1.
Не переименовывай продукт. Не пиши новый мессенджер.
Reuse: workspaces, delivery/Agent Ops, chats, attachments.
Feature-flag: ladya_hub_enabled (default false).

После M0: остановись, кратко отчитайся (файлы, как проверить вручную, что отложено).
Коммиты мелкие; push и PR — только если попрошу.
```

---

## 9. Связь с общей «Ладьёй»

Этот контур — **инструмент координации**, не доказательство готовности методологии или Lab-0.  
Руководящий обзор лабораторий: в репозитории `ladya_main_test` → `canon/ЛАДЬЯ_ОБЩИЙ_ПУТЬ_ЛАБОРАТОРИЙ.pdf`.  
При конфликте «мы уже готовы» vs обзор — побеждает обзор: Lab-0 и основная Ладья этим ТЗ не принимаются.

---

## 10. Открытые решения (зафиксировать в ADR на старте M0)

1. Laboratory как сущность внутри Workspace **или** Workspace = Laboratory?  
   **Рекомендация ТЗ:** сущность внутри одного «Ladya» workspace (проще права и чат портфеля).  
2. Носитель работы: DeliveryTask vs Kanban Card?  
   **Рекомендация:** DeliveryTask при `agent_ops_enabled`, иначе Card; в M0 достаточно FK nullable + ручная связь.  
3. Анонимный публичный Intake?  
   **Рекомендация M0:** только authenticated user; публичная форма — M1 с rate-limit и moderation.
