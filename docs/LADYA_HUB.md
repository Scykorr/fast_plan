# Ladya Hub (контур лабораторий на Fast Plan)

Операционный контур: лаборатории передают друг другу **пакеты** (задача + файлы + статус), люди пишут во **вход (Intake)**. Агенты по-прежнему берут работу только через Agent Ops inbox/handoff — не из сырого чата.

ТЗ: [`TZ_LADYA_HUB_ON_FAST_PLAN_v0.1.md`](TZ_LADYA_HUB_ON_FAST_PLAN_v0.1.md)  
ADR: [`adr-ladya-hub.md`](adr-ladya-hub.md)

## Включить флаг

1. Войти в workspace (редактор/владелец).
2. **Настройки** → блок «Ладья» → включить `ladya_hub_enabled`.
3. Или API:

```http
PATCH /api/ladya/settings/
X-Workspace-Id: <id>
{"ladya_hub_enabled": true}
```

Env default (обычно `false`): `LADYA_HUB_ENABLED_DEFAULT=false`.

После включения в сайдбаре появляется раздел **Ладья**.

## Создать лаборатории

UI: Ладья → Лаборатории, или:

```http
POST /api/ladya/laboratories/
{"slug": "central", "title": "Центральный ЛАД", "kind": "central_lad"}
POST /api/ladya/laboratories/
{"slug": "nikita", "title": "Lab Никита", "kind": "private_lab"}
```

Kinds: `central_lad` | `lab0` | `private_lab` | `external_intake`.

## Пакет с файлом и статусами

```http
POST /api/ladya/packages/
{"title": "Методологический возврат", "from_laboratory": 1, "to_laboratory": 2}

POST /api/ladya/packages/<id>/transition/
{"status": "submitted", "reason": "на приёмку"}

POST /api/ladya/packages/<id>/transition/
{"status": "accepted"}

POST /api/ladya/packages/<id>/files/
Content-Type: multipart/form-data
file: <binary>   # сервер считает sha256; лимит = ATTACHMENT_MAX_BYTES

POST /api/ladya/packages/<id>/transition/
{"status": "in_progress"}
POST /api/ladya/packages/<id>/transition/
{"status": "closed"}
```

Переходы: `draft → submitted → accepted → in_progress → returned|closed`; также `rejected` с допустимых шагов. Терминалы: `closed`, `rejected`.

## Intake → Package

```http
POST /api/ladya/intake/
{"body": "Нужна помощь", "contact": "@user", "source": "web_form"}

POST /api/ladya/intake/<id>/convert/
{"title": "Из обращения", "to_laboratory": 1}
```

В M0 intake только для authenticated участников workspace (viewer может создать обращение).

## Что не в M0

См. ТЗ §6 (M1): chunked/S3, связка Package↔DeliveryTask claim из UI, Telegram, комнаты чата на Laboratory, роли ЛАД/Картограф/Квест, zip+MANIFEST.
