# Сценарий мультиагентной передачи работы

Рабочий контур для CryptoGamp: отдельные учётки агентов, журнал задачи, явная передача, Git-поля, экран «Мои задачи».

Как заказчик это формулирует своими словами (чат → inbox → git → передача) и как это совпадает с ТЗ: [CUSTOMER_AGENT_LOOP.md](CUSTOMER_AGENT_LOOP.md).

Подробности продукта: [AGENT_OPS.md](AGENT_OPS.md). Исходное уточнение заказчика — август 2026.

## Приёмка (первый этап)

1. Owner создаёт задачу в эпике и назначает Backend Agent.
2. Агент видит её в `GET /api/delivery/my-tasks/` → «новые назначения» / «в работе».
3. Оставляет запись `kind=result` и ветку `github_branch` / `github_commits`.
4. `POST /api/delivery/tasks/{id}/handoffs/` на QA Agent (`to_user`, `reason`, `expected_next_step`).
5. QA видит задачу в своих корзинах, читает журнал, пишет `review_finding`.
6. Возвращает в разработку (`needs_rework`) или передаёт Owner (`ready_for_owner`).
7. Owner видит полную историю на карточке `/agent-ops?task=`.

Состояние и исполнитель разделены: например статус «На проверке» (`qa`) и исполнитель QA Agent.
