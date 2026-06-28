# Fast Plan

Личный мультипользовательский планировщик: Kanban-заметки и календарь дней рождения.

## Стек

- **Backend:** Django 6 + DRF + JWT
- **Frontend:** React + TypeScript + Vite + Tailwind

## Быстрый старт

**Запуск всего проекта одной командой (Windows):**

```bat
run.bat
```

Откроются два окна: backend и frontend. Сайт: http://localhost:5173

### Backend

```bash
# Активировать venv и установить зависимости
pip install -r requirements.txt

cd backend
python manage.py migrate
python manage.py runserver
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Приложение: http://localhost:5173 (API проксируется на :8000)

### Тесты

```bash
# Backend
cd backend && pytest

# Frontend
cd frontend && npm test
```

Подробный план разработки — в [PLAN.md](PLAN.md).
