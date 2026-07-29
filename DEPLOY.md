# Развёртывание Fast Plan на своём сервере

Инструкция для **production / self-hosted** установки через Docker Compose и для **обновлений без потери данных**.

Связанные документы:

- локальная разработка — [`README.md`](README.md)
- staging-чеклист — [`STAGING.md`](STAGING.md)
- безопасность и бэкапы — [`SECURITY.md`](SECURITY.md)
- версии — [`VERSION`](VERSION), [`CHANGELOG.md`](CHANGELOG.md)

---

## 1. Что сохраняется при обновлениях

| Данные | Где живут | Переживают `docker compose up --build`? |
|--------|-----------|------------------------------------------|
| PostgreSQL (пользователи, проекты, CRM, Agent Ops…) | том `postgres_data` | **Да** |
| Redis (кэш, Celery, SSE) | том `redis_data` | **Да** (можно сбрасывать) |
| Секреты и настройки | файл `.env` на хосте | **Да**, если не перезаписывать |
| Загруженные файлы (вложения, аватары) | `MEDIA_ROOT` внутри контейнера (`/app/media`) | **Нет**, пока не смонтирован том (см. §3.4) |
| Код приложения | образ backend/frontend | Пересобирается из git |

**Критично:** не удаляйте Docker-тома (`docker compose down -v`, `docker volume rm …`) — это сотрёт базу.

Миграции Django запускаются автоматически при старте backend (`entrypoint.sh`: `migrate --noinput`). Старые данные остаются; схема обновляется вперёд.

---

## 2. Требования к серверу

Минимум (см. также ТЗ Agent Ops / ops notes):

- Linux (Ubuntu 22.04+ / Debian 12+ и аналоги)
- Docker Engine + Docker Compose v2
- ≥ 4 CPU, ≥ 8–16 GB RAM, SSD
- Открытые порты: `80`/`443` (через reverse proxy), при прямом доступе — `8080` (frontend), опционально `8000` (API)
- Домен или внутреннее DNS-имя (для HTTPS и cookie/CSRF)

Проверка:

```bash
docker --version
docker compose version
```

---

## 3. Первичное развёртывание

### 3.1. Клонирование

```bash
sudo mkdir -p /opt/fast_plan
sudo chown "$USER":"$USER" /opt/fast_plan
cd /opt/fast_plan
git clone https://github.com/Scykorr/fast_plan.git .
# или: git clone <ваш-fork> .
```

Зафиксируйте релизный тег или `main` — что используете как канал обновлений.

### 3.2. Файл `.env`

```bash
cp .env.example .env
chmod 600 .env
nano .env   # или другой редактор
```

Обязательно задайте:

| Переменная | Назначение |
|------------|------------|
| `DJANGO_SECRET_KEY` | ≥ 32 случайных символа, не `change-me` / `insecure` |
| `POSTGRES_PASSWORD` | сильный пароль БД |
| `DJANGO_ALLOWED_HOSTS` | домен API/хоста, например `plan.example.com,backend` |
| `CORS_ALLOWED_ORIGINS` | URL SPA, например `https://plan.example.com` |
| `CSRF_TRUSTED_ORIGINS` | то же с схемой, например `https://plan.example.com` |
| `FRONTEND_BASE_URL` | публичный URL SPA (письма, invite, OAuth return) |

Для production за reverse proxy с HTTPS:

```env
DJANGO_DEBUG=false
DJANGO_SECURE_SSL_REDIRECT=true
# DJANGO_COOKIE_SECURE=true   # обычно следует из SSL redirect
```

Рекомендуется сразу:

```env
REDIS_URL=redis://redis:6379/1
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
CELERY_TASK_ALWAYS_EAGER=false
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=...
EMAIL_HOST_USER=...
EMAIL_HOST_PASSWORD=...
DEFAULT_FROM_EMAIL=Fast Plan <noreply@example.com>
```

Опционально: `SENTRY_DSN`, `VAPID_*` (Web Push), OAuth Microsoft/Google (SSO / календарь), `OPENAI_*` / `OLLAMA_*`.

### 3.3. Запуск стека

```bash
cd /opt/fast_plan
docker compose up -d --build
```

Сервисы по умолчанию: `db`, `redis`, `backend`, `celery-worker`, `celery-beat`, `frontend`.

| URL | Что |
|-----|-----|
| http://SERVER:8080 | SPA + прокси `/api/` → backend |
| http://SERVER:8000 | Backend напрямую (лучше закрыть снаружи) |

Проверка:

```bash
curl -s http://127.0.0.1:8000/api/health/
curl -s "http://127.0.0.1:8000/api/health/?extended=1"
docker compose ps
docker compose logs -f backend
```

Ожидается `"status": "ok"` и `version` = содержимое `VERSION`.

Первого пользователя создайте через UI регистрации **или**:

```bash
docker compose exec backend python manage.py createsuperuser
```

### 3.4. Том для медиафайлов (настоятельно рекомендуется)

В базовом `docker-compose.yml` каталог `/app/media` **не** вынесен в volume: после пересборки backend вложения и аватары могут пропасть.

Добавьте на сервере override (не коммитьте секреты):

```bash
# /opt/fast_plan/docker-compose.override.yml
services:
  backend:
    volumes:
      - media_data:/app/media
  celery-worker:
    volumes:
      - media_data:/app/media
  celery-beat:
    volumes:
      - media_data:/app/media

volumes:
  media_data:
```

Затем:

```bash
docker compose up -d --build
```

### 3.5. HTTPS (reverse proxy)

Типичная схема: **Caddy / Nginx / Traefik** на хосте → `127.0.0.1:8080` (frontend уже проксирует `/api/` в backend).

Пример Nginx (фрагмент):

```nginx
server {
    listen 443 ssl http2;
    server_name plan.example.com;
    # ssl_certificate …; ssl_certificate_key …;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        # SSE / long requests:
        proxy_read_timeout 3600s;
        proxy_buffering off;
    }
}
```

После включения HTTPS обновите в `.env`: `FRONTEND_BASE_URL`, `CORS_*`, `CSRF_*`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_SECURE_SSL_REDIRECT=true`, затем:

```bash
docker compose up -d
```

Не публикуйте порт `8000` наружу, если весь трафик идёт через `8080`/прокси.

### 3.6. Опциональные профили

```bash
# Локальный LLM (AI-черновики)
# В .env: OLLAMA_BASE_URL=http://ollama:11434
docker compose --profile ai up -d

# Live Asterisk ARI bridge (телефония)
docker compose --profile telephony up -d
```

---

## 4. Обновление без потери данных

Цель: новый код + миграции БД, **те же** тома Postgres/Redis/media и тот же `.env`.

### 4.1. Перед обновлением (обязательно)

1. Сообщите пользователям о коротком окне обслуживания (обычно минуты).
2. Сделайте бэкап БД (§5).
3. При смонтированном media — бэкап каталога/тома media.
4. Сохраните копию `.env` (не в git).

```bash
cd /opt/fast_plan
mkdir -p /opt/fast_plan/backups
TS=$(date +%Y%m%d_%H%M%S)
docker compose exec -T db \
  pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc \
  > "/opt/fast_plan/backups/fast_plan_${TS}.dump"
# либо без переменных из shell:
# docker compose exec -T db pg_dump -U fast_plan -d fast_plan -Fc > backups/fast_plan_${TS}.dump
cp -a .env "backups/env_${TS}.bak"
```

Проверьте, что том Postgres существует:

```bash
docker volume ls | grep postgres
```

### 4.2. Стандартный путь обновления

```bash
cd /opt/fast_plan

# 1) Код
git fetch --tags
git pull --ff-only
# или: git checkout v0.15.0 && git pull --ff-only

# 2) Прочитать CHANGELOG.md — breaking changes / новые env

# 3) Пересобрать и поднять (тома НЕ трогать)
docker compose up -d --build

# 4) Проверить
curl -s http://127.0.0.1:8000/api/health/
curl -s "http://127.0.0.1:8000/api/health/?extended=1"
docker compose logs --tail=100 backend
docker compose ps
```

Что происходит:

1. Образы `backend` / `frontend` / celery пересобираются.
2. Контейнеры пересоздаются.
3. Том `postgres_data` подключается снова → данные на месте.
4. `entrypoint.sh` выполняет `migrate --noinput` → схема догоняет код.
5. Frontend отдаёт новый SPA; PWA может показать «Доступна новая версия».

**Не делайте:**

```bash
docker compose down -v          # удалит тома с данными!
docker volume prune             # опасно на общем Docker-хосте
rm -rf /var/lib/docker/volumes  # катастрофа
```

Безопасно остановить без потери данных:

```bash
docker compose down             # тома сохраняются
docker compose up -d --build
```

### 4.3. Если нужны новые переменные окружения

После `git pull` сравните `.env.example` с вашим `.env`, добавьте недостающие ключи **вручную**, не копируя `.env.example` поверх рабочего `.env`.

```bash
# пример осторожной сверки
diff -u .env .env.example || true
```

### 4.4. Долгие миграции

Обычные релизы — быстрые `migrate`. Если в `CHANGELOG` указан тяжёлый data-migration:

1. Бэкап (§4.1).
2. `docker compose up -d --build`.
3. Следите за логами: `docker compose logs -f backend`.
4. Не прерывайте контейнер во время migrate.

Принудительный migrate (если уже поднят стек):

```bash
docker compose exec backend python manage.py migrate --noinput
docker compose exec backend python manage.py showmigrations
```

### 4.5. Откат (rollback)

Код можно откатить; **откат миграций Django** — только если в релизе это явно описано. Обычно безопаснее:

1. Восстановить БД из дампа (§5.2).
2. Checkout предыдущего тега.
3. `docker compose up -d --build`.

```bash
cd /opt/fast_plan
git checkout v0.14.2   # предыдущая рабочая версия
docker compose up -d --build
# при необходимости восстановить dump, сделанный ДО неудачного обновления
```

---

## 5. Резервное копирование и восстановление

### 5.1. Регулярный бэкап (cron)

Пример ежедневного скрипта — готовый [`scripts/backup-db.sh`](scripts/backup-db.sh)
(custom-format dump, retention, снимок `.env`, опционально GPG через `BACKUP_GPG_RECIPIENT`,
media tarball). Мини-вариант:

```bash
#!/bin/sh
set -e
ROOT=/opt/fast_plan
KEEP_DAYS=14
TS=$(date +%Y%m%d_%H%M%S)
mkdir -p "$ROOT/backups"
cd "$ROOT"
docker compose exec -T db pg_dump -U fast_plan -d fast_plan -Fc \
  > "$ROOT/backups/fast_plan_${TS}.dump"
find "$ROOT/backups" -name 'fast_plan_*.dump' -mtime +$KEEP_DAYS -delete
```

```bash
chmod +x /opt/fast_plan/scripts/backup-db.sh
# crontab -e → 0 3 * * * /opt/fast_plan/scripts/backup-db.sh
# с шифрованием: BACKUP_GPG_RECIPIENT=ops@example.com /opt/fast_plan/scripts/backup-db.sh
```

Храните копии **вне** сервера приложения (S3, другой диск, другой хост). См. [`SECURITY.md`](SECURITY.md).

### 5.2. Восстановление БД

```bash
cd /opt/fast_plan
docker compose stop backend celery-worker celery-beat frontend
# осторожно: перезапишет текущую БД
docker compose exec -T db pg_restore -U fast_plan -d fast_plan --clean --if-exists \
  < backups/fast_plan_YYYYMMDD_HHMMSS.dump
docker compose start backend celery-worker celery-beat frontend
docker compose exec backend python manage.py migrate --noinput
```

При несовместимости флагов `pg_restore` используйте plain SQL dump (`pg_dump` без `-Fc`) и `psql < dump.sql`.

### 5.3. Restore drill (staging, без порчи боевых данных)

Раз в квартал (или после крупного релиза) прогоняйте [`scripts/restore-drill.sh`](scripts/restore-drill.sh):

1. Делает свежий `pg_dump` живой БД (или берёт `DUMP_PATH`).
2. Создаёт отдельную БД `fast_plan_restore_drill`.
3. Восстанавливает dump туда и проверяет число таблиц.
4. Удаляет drill-БД. **Живая `POSTGRES_DB` не перезаписывается.**

```bash
cd /opt/fast_plan
chmod +x scripts/restore-drill.sh
HEALTH_URL=https://staging.example/api/health/ ./scripts/restore-drill.sh
# или только проверка существующего dump:
# SKIP_BACKUP=1 DUMP_PATH=backups/fast_plan_YYYYMMDD_HHMMSS.dump ./scripts/restore-drill.sh
```

Критерий успеха: скрипт печатает `ok restore drill passed` и live `/api/health/` (если задан `HEALTH_URL`) остаётся зелёным.

### Restore-drill log

| Date | Env | Dump | Tables in drill DB | Notes |
|------|-----|------|--------------------|-------|
| 2026-07-29 | local compose staging stand-in (`HEALTH_URL=http://127.0.0.1:8000/api/health/`) | `backups/fast_plan_20260729_204836.dump` | 123 | Passed; live DB untouched. Full ops row in [`STAGING.md`](STAGING.md) § Ops log. |

---

## 6. Операционные команды

```bash
# Статус
docker compose ps
docker compose logs -f backend celery-worker

# Shell в backend
docker compose exec backend bash
docker compose exec backend python manage.py shell

# VAPID keys для Web Push
docker compose exec backend python manage.py generate_vapid_keys

# Smoke-фикстуры (только staging/dev, не на боевых данных!)
# docker compose exec backend python manage.py ensure_smoke_fixtures --json
```

---

## 7. Чеклист после деплоя / обновления

- [ ] `GET /api/health/` → `ok`, версия = `VERSION`
- [ ] `GET /api/health/?extended=1` → database ok, redis ok, celery не eager
- [ ] Вход в UI, существующие проекты/CRM на месте
- [ ] Вложения открываются (если смонтирован media volume)
- [ ] Письма (invite / reset) при настроенном SMTP
- [ ] Celery: reminders / webhooks в логах worker
- [ ] HTTPS и CSRF/CORS соответствуют домену
- [ ] Staging-чеклист по необходимости: [`STAGING.md`](STAGING.md)

---

## 8. Частые проблемы

| Симптом | Что проверить |
|---------|----------------|
| 502 / frontend без API | `docker compose ps`, логи `backend`, сеть Compose |
| CSRF / cookie login fail | `CSRF_TRUSTED_ORIGINS`, `FRONTEND_BASE_URL`, HTTPS + `X-Forwarded-Proto` |
| Пустая БД после «обновления» | Не использовали ли `down -v`? Есть ли том `…_postgres_data`? |
| Пропали файлы | Не смонтирован `media_data` — см. §3.4 |
| Migrate failed | Логи backend; откат к дампу + предыдущий тег |
| SSE не работает на нескольких workers | `REDIS_URL` обязателен |

---

## 9. Краткий шпаргалка

**Первый запуск:**

```bash
cp .env.example .env && nano .env
# добавить docker-compose.override.yml с media_data (§3.4)
docker compose up -d --build
```

**Обновление:**

```bash
# бэкап pg_dump → git pull → docker compose up -d --build → health check
# никогда: docker compose down -v
```
