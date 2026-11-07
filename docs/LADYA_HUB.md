# Ladya Hub (контур лабораторий на Fast Plan)

Операционный контур координации: лаборатории передают друг другу **пакеты** (задача + файлы + статус), люди пишут во **вход (Intake)**. Агенты по-прежнему берут работу только через Agent Ops inbox/handoff — не из сырого чата.

ТЗ: [`TZ_LADYA_HUB_ON_FAST_PLAN_v0.1.md`](TZ_LADYA_HUB_ON_FAST_PLAN_v0.1.md)  
ADR: [`adr-ladya-hub.md`](adr-ladya-hub.md)  
Ветка: **`feature/ladya-hub`** (не merge в main без явной просьбы).

## Брендинг (светлая тема)

Ассеты в `frontend/public/ladya/` (UI переключает по теме сайта):

**Светлая**
- `logo-mark.png` / `logo-mark.svg` — прозрачный знак
- `logo-light.png` — вариант mark
- `hero-light.jpg` — баннер шапки `/ladya`

**Тёмная**
- `logo-dark-mark.png` / `logo-dark-mark.svg` — прозрачный electric-blue знак
- `logo-dark.jpg` — исходный вид на чёрном фоне
- `hero-dark.jpg` — баннер шапки для dark mode

Пересборка: `python scripts/prepare_ladya_assets.py`, `python scripts/prepare_ladya_dark_assets.py`.

## Включить флаг

1. Войти в workspace (редактор/владелец).
2. **Настройки** → блок «Ладья» → включить `ladya_hub_enabled`.
3. Или API:

```http
PATCH /api/ladya/settings/
X-Workspace-Id: <id>
{"ladya_hub_enabled": true}
```

Env: `LADYA_HUB_ENABLED_DEFAULT=false` (default).

## Лаборатории и пакеты

```http
POST /api/ladya/laboratories/
{"slug": "central", "title": "Центральный ЛАД", "kind": "central_lad"}

POST /api/ladya/packages/
{"title": "…", "from_laboratory": 1, "to_laboratory": 2}

POST /api/ladya/packages/<id>/transition/
{"status": "submitted", "reason": "…"}
```

### Крупные файлы (M1)

- Лимит: env **`LADYA_PACKAGE_MAX_BYTES`** (default **256 MiB**), отдельно от `ATTACHMENT_MAX_BYTES`.
- Hash: потоковый sha256 на сервере (chunks), без удержания всего файла в RAM.
- Self-host: для upload > proxy body limit увеличьте `client_max_body_size` в nginx / reverse-proxy и при необходимости Django `DATA_UPLOAD_MAX_MEMORY_SIZE` (большие файлы всё равно уходят во временный файл на диск).
- Chunked/S3 — зарезервировано на следующий этап (интерфейс PackageFile уже с sha256/size).

```http
POST /api/ladya/packages/<id>/files/   # multipart file
```

### Передача между лабораториями

```http
POST /api/ladya/packages/<id>/transfer/
{"to_laboratory": 2, "reason": "возврат в ЛАД"}
```

Разрешено из `accepted` | `in_progress` | `returned`. Пишет `PackageStatusEvent`.

### DeliveryTask из пакета

```http
POST /api/ladya/packages/<id>/create-delivery-task/
```

Создаёт draft DeliveryTask, линкует FK, **без auto-claim**. Агенты — только через inbox.

### Манифест

```http
POST /api/ladya/packages/<id>/manifest/   # считает manifest_sha256
GET  /api/ladya/packages/<id>/manifest/   # скачать JSON
```

## Intake → Package

Человек пишет во **Вход**; ЛАД triagе/convert → Package.

```http
POST /api/ladya/intake/
{"body": "…", "contact": "@user", "source": "web_form"}

POST /api/ladya/intake/<id>/triage/
{"status": "triaged"}   # или closed

POST /api/ladya/intake/<id>/convert/
{"to_laboratory": 1}    # обязателен; title по умолчанию из начала body
```

В этом контуре intake только для authenticated участников workspace (viewer может создать). Публичный анонимный endpoint без rate-limit — не включён.

## Фильтры и лаборатория

```http
GET /api/ladya/packages/?status=accepted&from_lab=1&to_lab=2&q=текст
GET /api/ladya/laboratories/<id>/packages/?direction=incoming|outgoing|all
GET /api/ladya/events/?limit=30
```

## Ручная проверка за 5–10 минут

1. Settings → включить Ладью.
2. Создать central_lad + private_lab.
3. Пакет → submitted → accepted → файл → transfer в другую lab → create DeliveryTask.
4. Intake → triage → convert (to central) → Package.
5. Манифест → скачать JSON, сверить `manifest_sha256`.

## Человек → ЛАД через внутренний чат

**Telegram для Ладьи out of scope.** CRM Telegram webhooks не трогаем и не расширяем под Laboratory/Package/Intake.

Каналы входа:

1. Форма **Ладья → Вход** (`source=web_form`).
2. Внутренний чат Fast Plan: на `central_lad` / `external_intake` нажмите **Создать комнату лаборатории** (привязка к чату портфеля `/portfolio`). Editor на сообщении → **Создать Intake** (`source=internal_chat`). Без автосоздания на каждое сообщение.

```http
POST /api/ladya/laboratories/<id>/ensure-chat/
POST /api/ladya/intake/from-chat-message/
{"message_id": 123}
POST /api/ladya/packages/<id>/notify-chat/   # явный клик, не spam при transition
```

Новый Intake (форма или чат) → in-app notification editors/owners.

## Подключение агентов

Мастер **Ладья → Агенты**: выбрать lab + роль → создать service account → скопировать карточку (credentials + правила). Вставить в **любой** агентный рантайм (Cursor / Codex / Claude / …) — Fast Plan API один и тот же. Шпаргалка: [`LADYA_CONNECT_AGENT.md`](LADYA_CONNECT_AGENT.md).

```http
POST /api/ladya/agents/
{"ladya_role": "quest", "laboratory": 1, "display_name": "Quest bot"}
```

Роли: [`LADYA_ROLES.md`](LADYA_ROLES.md). `Package.preferred_role` — hint. Агенты — только через Agent Ops inbox.

## Чат лаборатории

`Laboratory.chat_room` → существующий ChatRoom (в пилоте — единый workspace portfolio chat). Отдельные lab rooms / Matrix / Signal E2E — отложены (ADR).

## Не в scope (позже)

Telegram для Ladya; chunked/S3; свой мессенджер; анонимный публичный intake; merge в main; приёмка Lab-0.
