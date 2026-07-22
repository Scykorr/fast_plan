# Staging checklist

Чеклист проверки Fast Plan на staging/pre-production окружении.
Отмечайте `[x]` после успешной проверки; фиксируйте дату и окружение в комментарии.

## Перед деплоем

- [ ] `VERSION`, `CHANGELOG.md`, `frontend/package.json`, `frontend/src/version.ts` синхронизированы (`node scripts/check-version-sync.mjs`)
- [ ] `.env` заполнен production-секретами (`DJANGO_SECRET_KEY`, `POSTGRES_PASSWORD`, SMTP)
- [ ] `DJANGO_DEBUG=false`, `DJANGO_SECURE_SSL_REDIRECT=true` (за HTTPS reverse proxy)
- [ ] `CORS_ALLOWED_ORIGINS` и `CSRF_TRUSTED_ORIGINS` содержат staging URL фронтенда
- [ ] `FRONTEND_BASE_URL` указывает на staging SPA (ссылки в письмах)
- [ ] Redis доступен (`REDIS_URL`), Celery worker + beat запущены (`CELERY_TASK_ALWAYS_EAGER=false`)
- [ ] Для multi-worker gunicorn: `REDIS_URL` обязателен также для SSE pub/sub (см. [`SECURITY.md`](SECURITY.md))

## Health и инфраструктура

```bash
# Автоматические проверки (локально или staging)
node scripts/staging-smoke-check.mjs --offline          # только sync VERSION
STAGING_BASE_URL=https://staging.example.com node scripts/staging-smoke-check.mjs

# CI: job staging-smoke поднимает docker-compose и прогоняет полный набор
# Локально после docker compose up:
docker compose exec backend python manage.py ensure_smoke_fixtures --json
```

### Ollama (локальный LLM для AI-черновиков)

```bash
# Вариант A — Ollama на хосте
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=llama3.2
ollama pull llama3.2

# Вариант B — Docker Compose profile `ai`
# В .env:
# OLLAMA_BASE_URL=http://ollama:11434
# OLLAMA_MODEL=llama3.2
docker compose --profile ai up -d ollama ollama-init backend
```

В UI «AI-черновик» источник отображается как **Ollama**; без OpenAI/Ollama используется встроенная эвристика.

- [ ] `node scripts/staging-smoke-check.mjs` проходит без ошибок (warnings допустимы)

- [ ] `GET /api/health/` → `{ "status": "ok", "version": "…" }` совпадает с `VERSION`
- [ ] `GET /api/health/?extended=1` → `checks.database` = `ok`
- [ ] `checks.redis` = `ok` (или `skipped` при locmem — не для production)
- [ ] `checks.celery_eager` = `false` на staging

## SMTP и email verification

- [ ] `EMAIL_BACKEND` = SMTP, не console
- [ ] `DEFAULT_FROM_EMAIL` и SMTP credentials проверены
- [ ] Регистрация нового пользователя → письмо с подтверждением приходит
- [ ] Ссылка `/verify-email?uid=…&token=…` подтверждает аккаунт
- [ ] Login до подтверждения email отклоняется (или ограничен — по политике)
- [ ] Settings → «Подтвердить email» повторно отправляет письмо
- [ ] Invite участника workspace → письмо с ссылкой `/invite/accept/…`

## Webhooks

- [ ] Settings (owner) → создать webhook на тестовый HTTPS endpoint (например webhook.site)
- [ ] Кнопка **Тест** → доставка со статусом `queued`, запись в `WebhookDelivery`
- [ ] Celery worker обрабатывает доставку (проверить HTTP status в журнале или на приёмнике)
- [ ] Создание риска в проекте → событие `risk.created` на endpoint (если подписан)
- [ ] HMAC-подпись `X-Fast-Plan-Signature: sha256=…` валидна на стороне приёмника

## PWA install / update

- [ ] Frontend собран с `vite-plugin-pwa` (`npm run build`)
- [ ] Manifest доступен, `theme_color` и иконки загружаются
- [ ] Service worker регистрируется (DevTools → Application → Service Workers)
- [ ] На мобильном/Chrome: «Установить приложение» доступно (standalone)
- [ ] Offline: shell открывается без сети (навигация SPA)
- [ ] После деплоя новой версии появляется toast «Доступна новая версия» → **Обновить** перезагружает SW
- [ ] `VAPID_*` в `.env` (см. `python manage.py generate_vapid_keys`); Settings → «Включить push»
- [ ] Офлайн: создать CRM-активность без сети → баннер очереди → после online синхронизация

## E2E Playwright (login / PWA / SSE)

```bash
# Поднять стек и фикстуры
docker compose up -d --build db redis backend frontend
FIXTURES=$(docker compose exec -T backend python manage.py ensure_smoke_fixtures --json)

cd e2e && npm ci
npx playwright install chromium
E2E_BASE_URL=http://127.0.0.1:8080 \
E2E_EMAIL=$(echo "$FIXTURES" | python -c "import sys,json; print(json.load(sys.stdin)['email'])") \
E2E_PASSWORD=$(echo "$FIXTURES" | python -c "import sys,json; print(json.load(sys.stdin)['password'])") \
E2E_WORKSPACE_ID=$(echo "$FIXTURES" | python -c "import sys,json; print(json.load(sys.stdin)['workspace_id'])") \
E2E_PROJECT_ID=$(echo "$FIXTURES" | python -c "import sys,json; print(json.load(sys.stdin)['project_id'])") \
npm test
```

CI: job `e2e` в `.github/workflows/ci.yml` (login, manifest/SW, SSE toast smoke).

- [ ] `npm test` в `e2e/` проходит против staging или локального compose

## Smoke после деплоя

- [ ] Login / logout, переключение workspace
- [ ] Создание проекта, WBS-узел, риск, транзакция Finance
- [ ] SSE toast при изменении Kanban/WBS (два браузера)
- [ ] Guest share link `/share/:token` открывается без авторизации

---

При обнаружении регрессии — запись в `CHANGELOG.md` → `[Unreleased]` и задача в `ROADMAP.md`.
