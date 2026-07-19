# Roadmap / улучшения

Живой бэклог: что сделать дальше и что улучшить в текущем коде.
Обновляется по мере разработки. Приоритет сверху вниз.

## P0 — закрыть дыры в уже заявленных возможностях

_Выполнено (2026-07-19): invite UI, RBAC owner/editor/viewer, workspace switcher._

## P1 — UX и качество продукта

1. **Дашборд как командный центр**  
   Сейчас в основном приветствие + ДР. Добавить просроченные задачи, риски, SPI/CPI, непрочитанные уведомления.

2. **Формы вместо `window.prompt`**  
   Finance, Administration, часть Settings — полноценные формы разблокируют поля API (тип транзакции, роль инвайта и т.д.).

3. **Фильтры Kanban/WBS и deep-link из уведомлений**  
   Открывать карточку/узел из колокольчика; фильтр по исполнителю/статусу.

## P2 — техника и эксплуатация

4. **Расширить coverage в CI**  
   Сейчас cov только accounts/workspaces/kanban/birthdays; добавить projects, finance, tracking, notifications.

5. **Production hardening**  
   Падать при insecure `SECRET_KEY` если `DEBUG=false`; HSTS/secure cookies; не хардкодить секреты в compose.

6. **JWT не в `localStorage`**  
    Предпочтительно httpOnly cookie (или короткий access + аккуратный refresh).

7. **Фоновые напоминания**  
    Birthday/deadline notifications не должны зависеть только от открытия списка — Celery/cron + management command.

## P3 — следующие фичи (PM)

8. PDF / digest статус-отчёта (сейчас экспорт JSON)
9. Комментарии / лог решений на WBS и карточках
10. Глобальный поиск + «Мои задачи» (по `assignee`)
11. Загрузка ресурсов / capacity по неделе

---

При реализации пункта: перенести в `CHANGELOG.md` (Unreleased → релиз) и вычеркнуть/перенести сюда следующий приоритет.
