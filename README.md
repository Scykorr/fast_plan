# Fast Plan

Личный мультипользовательский планировщик: Kanban-заметки и календарь дней рождения.

## Стек

- **Backend:** Django 6 + DRF + JWT + PostgreSQL
- **Frontend:** React + TypeScript + Vite + Tailwind
- **Инфраструктура:** Docker Compose, GitHub Actions CI

## Быстрый старт (локально)

**Windows — одной командой:**

```bat
run.bat
```

Откроются два окна: backend и frontend. Сайт: http://localhost:5173

### Backend

```bash
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

API проксируется на http://127.0.0.1:8000

## Docker Compose

```bash
docker compose up --build
```

- **Frontend:** http://localhost:8080
- **Backend API:** http://localhost:8000
- **PostgreSQL:** внутренняя сеть Docker

## Тесты

```bash
# Backend
cd backend && pytest

# Frontend
cd frontend && npm test
```

CI запускает оба набора тестов на каждый push/PR в `main`.

Подробный план разработки — в [PLAN.md](PLAN.md).
