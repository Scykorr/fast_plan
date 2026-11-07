# Роли Ладьи (справочник)

Короткая карта ролей для контура Ladya Hub на Fast Plan. Это **не** приёмка Lab-0 и не полный методологический канон.

## Человек-ЛАД vs роль-агент

| Кто | Где в Fast Plan | Что делает |
| --- | --- | --- |
| **Человек-ЛАД / куратор** | Owner/Editor workspace + опционально `AgentProfile.ladya_role=curator` | Включает флаг, triagе Intake, convert → Package, transfer, закрывает/возвращает пакеты. Не «бот из Telegram». |
| **ЛАД (координатор)** | `ladya_role=lad` на service account Agent Ops | Берёт DeliveryTask через inbox/claim/handoff; ведёт передачу работы между лабораториями. |
| **Картограф** | `ladya_role=cartographer` | Структурирует карту/зависимости; hint через `Package.preferred_role`. |
| **Квест** | `ladya_role=quest` | Исполняет конкретный шаг/квест по связанной DeliveryTask. |

Роли Agent Ops (`backend`, `qa`, `planner`…) остаются техническими ACL. `ladya_role` — **справочник/отображение**, не enforcement ЖЦ пакета.

## Preferred role на пакете

`Package.preferred_role` — подсказка «кто следующий» (`lad` / `cartographer` / `quest` / `curator`). Не блокирует transition/transfer и не auto-assign.

## Что сознательно не объявляем готовым

- Lab-0 как продуктовая сущность «принята».
- Skills / Core центрального ЛАДа.
- Автозапуск агента из Telegram или сырого чата.
- Привязка рантайма к одной IDE: агент = любой клиент Fast Plan API (Cursor / Codex / Claude / …).

См. также: [`LADYA_HUB.md`](LADYA_HUB.md), [`adr-ladya-hub.md`](adr-ladya-hub.md).
