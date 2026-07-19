# Fast Plan

Личный мультипользовательский планировщик: Kanban, календарь дней рождения, проекты (WBS/Gantt), трекеры и кастомные поля.

**Текущая версия:** см. [`VERSION`](VERSION) · история изменений — [`CHANGELOG.md`](CHANGELOG.md) · бэклог — [`ROADMAP.md`](ROADMAP.md)

## Стек

- **Backend:** Django 6 + DRF + JWT + PostgreSQL
- **Frontend:** React + TypeScript + Vite + Tailwind
- **Инфраструктура:** Docker Compose, GitHub Actions CI

## Версионирование

Используем [Semantic Versioning](https://semver.org/lang/ru/) и [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/).

При релизе:

1. Обновить `VERSION` (например `0.4.0`)
2. Перенести пункты из `CHANGELOG.md` → `[Unreleased]` в новую секцию `[x.y.z] — YYYY-MM-DD`
3. Синхронизировать `frontend/package.json` и `frontend/src/version.ts`
4. Закоммитить: `chore(release): v0.4.0`
5. (Опционально) git-тег: `git tag v0.4.0`

`GET /api/health/` возвращает `{ "status": "ok", "version": "…" }`.

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
