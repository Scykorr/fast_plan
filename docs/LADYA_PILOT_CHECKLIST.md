# Чеклист пилота Ladya Hub (10–15 мин)

Ветка: `feature/ladya-hub`. Цель — один живой прогон «человек → ЛАД → лаборатории», не приёмка Lab-0.

## Подготовка

- [ ] Поднят Fast Plan с ветки (`run.bat` / `run-docker.bat`)
- [ ] Workspace: Настройки → **Ладья** → `ladya_hub_enabled = on`
- [ ] В сайдбаре виден раздел «Ладья»

## Лаборатории

- [ ] Создать `central_lad` (slug например `central`)
- [ ] Создать `lab0` (slug `lab0`)
- [ ] Создать 1–2 `private_lab` (например `anton-stand`, `nikita`)

## Вход человека

- [ ] Ладья → **Вход**: отправить Intake (текст + контакт)
- [ ] Triage → `triaged`
- [ ] Convert → Package с обязательным `to_laboratory` (обычно central)
- [ ] Intake.status = `converted`, пакет открывается

## Пакет

- [ ] Открыть Package: upload файла (zip при необходимости; лимит `LADYA_PACKAGE_MAX_BYTES`, default 256 MiB)
- [ ] Видны `sha256` и size
- [ ] **Собрать манифест** → скачан JSON, заполнен `manifest_sha256`
- [ ] Статусы: `submitted` → `accepted` (или дальше по сценарию)
- [ ] **Передать** в другую lab + reason → событие в истории
- [ ] **Создать задачу Agent Ops** → `linked_delivery_task` заполнен, без auto-claim
- [ ] Закрыть пакет (`closed`) или вернуть (`returned`)

## Изоляция / негатив (быстро)

- [ ] При выключенном флаге пункта «Ладья» нет / API 403
- [ ] Запрещённый переход (например draft→closed) → ошибка

## Боль / наблюдения (заполнить человеку)

| Что больно / чего не хватает | Критичность |
| --- | --- |
|  |  |
|  |  |
|  |  |

## P2 smoke (после основного пилота)

- [ ] Настройки → Ладья → сгенерировать Telegram webhook secret, скопировать path
- [ ] POST mock update на webhook → Intake `source=telegram` + notification editor
- [ ] Agent Ops → у service account выставить `ladya_role`
- [ ] На пакете выставить `preferred_role` (hint)
- [ ] На лаборатории привязать `chat_room` (или «чат workspace»)

## После пилота

Документация: [`LADYA_HUB.md`](LADYA_HUB.md), [`LADYA_ROLES.md`](LADYA_ROLES.md).
