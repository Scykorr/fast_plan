# ADR: Ladya Hub — лаборатории и пакеты на Fast Plan

**Status:** Accepted (2026-11-07)  
**Context:** Нужен операционный контур координации лабораторий «Ладья» без переименования продукта, без нового мессенджера и без приёмки Lab-0. Носитель — Fast Plan; философия «чат — диспетчер; доска — передача работы» сохраняется ([`CUSTOMER_AGENT_LOOP.md`](CUSTOMER_AGENT_LOOP.md)).

## Decision

1. **Laboratory внутри Workspace.** Один workspace с флагом `ladya_hub_enabled` содержит несколько `Laboratory` (`central_lad`, `lab0`, `private_lab`, `external_intake`). Не 1:1 Workspace=Lab — проще общие права, портфельный чат и изоляция по membership.
2. **Носитель работы.** `Package.linked_delivery_task` — nullable FK на `delivery.DeliveryTask`. В M0 связь ручная; claim/handoff из UI — M1. Kanban Card не дублируем.
3. **Истина по работе** = Package (+ опциональная DeliveryTask), не последнее сообщение в чате.
4. **Feature-flag.** `LadyaSettings.ladya_hub_enabled` (default `false`), зеркало `DeliverySettings`. API `/api/ladya/...` кроме GET/PATCH settings закрыт при выключенном флаге.
5. **Intake в M0** — только authenticated участник workspace (`source=web_form|manual`). Публичная анонимная форма — M1.
6. **Файлы.** `PackageFile` + потоковый `sha256`; лимит **`LADYA_PACKAGE_MAX_BYTES`** (default 256 MiB), отдельно от attachments. Chunked/S3 — следующий этап (TODO).
7. **Reuse.** workspaces (права/`X-Workspace-Id`), delivery (DeliveryTask), attachments (паттерн upload), chats не расширяем в M0.
8. **M1 операции.** Transfer между lab — отдельный action + audit; DeliveryTask создаётся из Package без claim; convert Intake требует `to_laboratory`; manifest JSON → `manifest_sha256` (без volatile `updated_at` в каноне).
9. **Internal chat instead of Telegram for Ladya.** Вход людей и пинги lab — через `backend/chats` (форма Intake + кнопка «Создать Intake» в комнате, привязанной к `central_lad` / `external_intake`). Telegram webhook для Ladya **не** используем; CRM telegram не расширяем. Агенты не стартуют из чата.
10. **Роли.** `AgentProfile.ladya_role` + `Package.preferred_role` — справочник/hint; ACL Agent Ops не ломаем.
11. **Chat link.** `Laboratory.chat_room` → существующий ChatRoom (пилот: один workspace portfolio room). **Отложено:** отдельные group lab rooms / Signal / Matrix E2E.
12. **Agent connect UX for humans.** Мастер `/ladya/agents` создаёт service account + one-time copy card; рантайм агента снаружи (Cursor/Codex). См. [`LADYA_CONNECT_AGENT.md`](LADYA_CONNECT_AGENT.md).

## Consequences

- Новый Django app `ladya`, UI-раздел «Ладья» скрыт без флага.
- Статусы Package и Intake — конечные автоматы с явной историей смены статуса.
- Агенты по-прежнему видят только свой Agent Ops inbox; Package сам по себе inbox агента не открывает (M1 — связка).

## Related

- ТЗ: [`TZ_LADYA_HUB_ON_FAST_PLAN_v0.1.md`](TZ_LADYA_HUB_ON_FAST_PLAN_v0.1.md)
- How-to: [`LADYA_HUB.md`](LADYA_HUB.md)
- Agent Ops: [`AGENT_OPS.md`](AGENT_OPS.md)
