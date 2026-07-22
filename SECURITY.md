# Security & operations notes — Fast Plan

## Authentication (P7 MVP)

- **JWT cookies** — `fp_access` / `fp_refresh` (HttpOnly). CSRF required for cookie-authenticated mutations.
- **2FA (TOTP)** — optional per user (`Settings → Безопасность`). Login returns `requires_2fa` + short-lived `pre_auth_token`; complete via `POST /api/auth/2fa/verify/`. Backup codes are one-time SHA-256 hashes.
- **Sessions** — each successful login/2FA registers an `AuthSession` by refresh `jti`. Owners can revoke sessions in Settings; revoke also blacklists outstanding refresh tokens when present.
- **IP allowlist** — optional per workspace (owner). Empty list = allow all. Enforced by `WorkspaceIpAllowlistMiddleware` on `/api/*` (auth/health/share/telegram webhook exempt).

SSO (Google/Microsoft) is **not** in MVP — tracked in ROADMAP.

## Redis & realtime

Set `REDIS_URL` in production so:

1. Django cache / Celery broker work across workers.
2. **SSE pub/sub** (`workspaces.events`) fans out to all gunicorn workers.

Without Redis, SSE stays in-process (fine for single worker / tests).

## Backup runbook (MVP)

1. **Database** — nightly `pg_dump` of Postgres (`POSTGRES_DB`). Store off-host; retain ≥ 7 days.
2. **Media** — back up `MEDIA_ROOT` (avatars, attachments) with the same cadence.
3. **Secrets** — `DJANGO_SECRET_KEY`, SMTP, Redis, Sentry DSN live in env / secret manager — never in git.
4. **Restore drill** — at least once per quarter: restore dump to a staging DB, run `migrate`, hit `/api/health/?extended=1`.
5. **Before destructive ops** — snapshot DB + confirm `REDIS_URL` and cookie/CSRF settings for the target environment (see [`STAGING.md`](STAGING.md)).

## Related docs

- Staging checklist: [`STAGING.md`](STAGING.md)
- Changelog: [`CHANGELOG.md`](CHANGELOG.md)
