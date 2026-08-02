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

### SSO и Process (0.12 smoke)

Автоматически в `staging-smoke-check.mjs` (при `STAGING_EMAIL`/`PASSWORD`):

- [ ] `GET /api/auth/oauth/providers/` — `google: false`; `microsoft` warn если не настроен
- [ ] При `STAGING_EXPECT_MICROSOFT_SSO=1` — `microsoft: true` и redirect start на `login.microsoftonline.com`
- [ ] `GET /api/process/metrics|mining|decisions|cases|packs/` → 200
- [ ] `GET /api/calendar/crm/?year=&month=` → 200 (CRM-события на календаре)

### Calendar 2-way + Telephony (0.14 smoke)

Автоматически в smoke (auth):

- [ ] `GET /api/crm/calendar/providers/` → `{ microsoft, google }`
- [ ] `GET /api/crm/calendar/connections/` → массив (поля `conflict_policy`, `open_conflicts`)
- [ ] `GET /api/crm/calendar/conflicts/` → массив
- [ ] `GET /api/crm/connectors/catalog/` содержит `telephony`

### Custom fields + Agent Ops (0.16 smoke)

Автоматически в `staging-smoke-check.mjs` (при auth):

- [x] `GET /api/crm/custom-fields/` → массив; `POST` definition + list includes key
- [x] `PATCH /api/delivery/settings/` → `agent_ops_enabled: true` (если было false)
- [x] `GET /api/delivery/overview|queue|agents/` → 200
- [x] `GET /api/crm/skus/` → массив

Ручная проверка:

- [ ] Settings → Calendar: Sync both / Pull, политика конфликтов ours/theirs/manual, resolve конфликтов
- [ ] `/crm-commerce` → telephony connector: `pbx=asterisk` (ARI) или `pbx=mango` (api_key+salt+extension); webhook CDR → Activity call
- [ ] Mango: в ЛК указать URL webhook; подпись `sign` обязательна при заданном `api_salt`
- [ ] Asterisk: проксировать AMI/ARI события на `/api/crm/connectors/webhooks/telephony/<token>/` (не только CDR)
- [ ] Click-to-call: Person/Deal/Lead «Позвонить» при наличии telephony-коннектора
- [ ] Asterisk live ARI: `docker compose --profile telephony up -d ari-bridge` или `run_ari_bridge`
- [ ] `/processes` — вкладки DMN / Метрики·Mining / CMMN; `/process-tasks` inbox
- [ ] Settings → Outlook/Google Calendar OAuth (нужны `OAUTH_*` + redirect URI `…/api/crm/calendar/oauth/{provider}/callback/`)

- [ ] `GET /api/health/` → `{ "status": "ok", "version": "…" }` совпадает с `VERSION`
- [ ] `GET /api/health/?extended=1` → `checks.database` = `ok`
- [ ] `checks.redis` = `ok` (или `skipped` при locmem — не для production)
- [ ] `checks.celery_eager` = `false` на staging

## SMTP и email verification

- [ ] `EMAIL_BACKEND` = SMTP, не console (см. `.env.example`)
- [ ] `DEFAULT_FROM_EMAIL` и SMTP credentials проверены
- [ ] Settings (owner) → **Почта / SMTP**: статус показывает SMTP + `configured`
- [ ] Settings → **Отправить тест** → письмо в inbox (не только spam)
- [ ] SPF / DKIM / DMARC для домена `From` (mail.ru / корпоративный DNS)
- [ ] Forgot-password: `POST /api/auth/password/forgot/` → письмо со ссылкой
- [ ] Invite участника workspace → письмо с ссылкой `/invite/accept/…`
- [ ] Digest reminders (Celery) доходят при настроенном SMTP
- [ ] После зелёного test-send: `REQUIRE_EMAIL_VERIFICATION=true` на staging
- [ ] Регистрация → письмо с подтверждением
- [ ] Ссылка `/verify-email?uid=…&token=…` подтверждает аккаунт
- [ ] Login до подтверждения email отклоняется
- [ ] Settings → «Подтвердить email» повторно отправляет письмо

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

## Ops log

| Date | Env | Actions | Result |
|------|-----|---------|--------|
| 2026-07-31 | local docker-compose (staging stand-in, frontend **8088**) | Release **v0.17.0** deploy (`compose up --build`); `migrate` confirms `crm.0014_sku_inventory_016`; smoke-check | Health **0.17.0**; smoke **34/34** (incl. `/api/crm/skus/`); redis/database ok |
| 2026-07-29 | local docker-compose (staging stand-in; frontend host port **8088** — host `:8080` occupied by EDB PEM) | `migrate` (incl. `crm.0013_custom_fields_016`); `ensure_smoke_fixtures`; `node scripts/staging-smoke-check.mjs` (custom fields + Agent Ops); `HEALTH_URL=…/api/health/ ./scripts/restore-drill.sh` | Smoke **33/33** (warnings: console email, Microsoft SSO unset). Extended health: database/redis **ok**, celery not eager. Restore-drill **ok** — dump → `fast_plan_restore_drill`, **123** public tables, live health ok, drill DB dropped. Live `POSTGRES_DB` untouched. |

If host port 8080 is busy: set `FRONTEND_HOST_PORT=8088` (and matching `FRONTEND_BASE_URL` / CORS / CSRF) in `.env`.

---

При обнаружении регрессии — запись в `CHANGELOG.md` → `[Unreleased]` и задача в `ROADMAP.md`.
