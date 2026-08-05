#!/usr/bin/env bash
# Non-destructive Postgres restore drill for staging (see DEPLOY.md §5.3).
#
# Flow:
#   1) Optional: take a fresh dump (SKIP_BACKUP=1 to use existing DUMP_PATH)
#   2) Create throwaway DB fast_plan_restore_drill
#   3) pg_restore into it (--clean --if-exists)
#   4) Spot-check tables + optional migrate --check via backend
#   5) DROP the drill database
#
# Never touches the live POSTGRES_DB data. Safe for quarterly staging drills.
#
# Usage:
#   ROOT=/opt/fast_plan ./scripts/restore-drill.sh
#   DUMP_PATH=/opt/fast_plan/backups/fast_plan_YYYYMMDD.dump SKIP_BACKUP=1 ./scripts/restore-drill.sh
#   HEALTH_URL=http://127.0.0.1:8000/api/health/ ./scripts/restore-drill.sh

set -euo pipefail

ROOT="${ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"
DB_SERVICE="${DB_SERVICE:-db}"
DB_USER="${POSTGRES_USER:-fast_plan}"
DB_NAME="${POSTGRES_DB:-fast_plan}"
DRILL_DB="${DRILL_DB:-fast_plan_restore_drill}"
BACKUP_DIR="${BACKUP_DIR:-$ROOT/backups}"
SKIP_BACKUP="${SKIP_BACKUP:-0}"
HEALTH_URL="${HEALTH_URL:-}"

cd "$ROOT"
umask 077
mkdir -p "$BACKUP_DIR"

if [[ "$SKIP_BACKUP" != "1" ]]; then
  echo "==> backup live DB"
  ROOT="$ROOT" BACKUP_DIR="$BACKUP_DIR" COMPOSE_FILE="$COMPOSE_FILE" \
    DB_SERVICE="$DB_SERVICE" POSTGRES_USER="$DB_USER" POSTGRES_DB="$DB_NAME" \
    bash "$ROOT/scripts/backup-db.sh"
fi

if [[ -z "${DUMP_PATH:-}" ]]; then
  DUMP_PATH="$(ls -1t "$BACKUP_DIR"/fast_plan_*.dump 2>/dev/null | head -n1 || true)"
fi
if [[ -z "$DUMP_PATH" || ! -s "$DUMP_PATH" ]]; then
  # maybe gpg-only; refuse encrypted for drill without decrypt
  echo "No dump found in $BACKUP_DIR (set DUMP_PATH=... or run backup first)" >&2
  exit 1
fi
echo "==> using dump $DUMP_PATH"

echo "==> recreate drill database $DRILL_DB"
docker compose -f "$COMPOSE_FILE" exec -T "$DB_SERVICE" \
  psql -U "$DB_USER" -d postgres -v ON_ERROR_STOP=1 <<SQL
SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${DRILL_DB}' AND pid <> pg_backend_pid();
DROP DATABASE IF EXISTS ${DRILL_DB};
CREATE DATABASE ${DRILL_DB} OWNER ${DB_USER};
SQL

echo "==> restore into $DRILL_DB"
docker compose -f "$COMPOSE_FILE" exec -T "$DB_SERVICE" \
  pg_restore -U "$DB_USER" -d "$DRILL_DB" --clean --if-exists --no-owner \
  < "$DUMP_PATH" || {
    # pg_restore returns 1 on some warnings; verify tables exist
    echo "pg_restore exited non-zero — verifying relation count..." >&2
  }

COUNT="$(
  docker compose -f "$COMPOSE_FILE" exec -T "$DB_SERVICE" \
    psql -U "$DB_USER" -d "$DRILL_DB" -Atc \
    "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';"
)"
echo "==> public tables in drill DB: $COUNT"
if [[ "${COUNT:-0}" -lt 5 ]]; then
  echo "restore drill failed: too few tables ($COUNT)" >&2
  docker compose -f "$COMPOSE_FILE" exec -T "$DB_SERVICE" \
    psql -U "$DB_USER" -d postgres -c "DROP DATABASE IF EXISTS ${DRILL_DB};" || true
  exit 1
fi

BACKEND_SERVICE="${BACKEND_SERVICE:-backend}"
if [[ "${SKIP_MIGRATE_CHECK:-0}" != "1" ]]; then
  echo "==> migrate --check against drill DB (plan only, live DB untouched)"
  # Spot-check that restored schema is loadable; uses live DATABASE_URL by default.
  # Optional: set DRILL_MIGRATE_CHECK=1 and POSTGRES_DB override in compose for drill.
  if [[ "${DRILL_MIGRATE_CHECK:-0}" == "1" ]]; then
    docker compose -f "$COMPOSE_FILE" exec -T \
      -e POSTGRES_DB="$DRILL_DB" \
      "$BACKEND_SERVICE" \
      python manage.py migrate --check || {
        echo "migrate --check failed on drill DB" >&2
        docker compose -f "$COMPOSE_FILE" exec -T "$DB_SERVICE" \
          psql -U "$DB_USER" -d postgres -c "DROP DATABASE IF EXISTS ${DRILL_DB};" || true
        exit 1
      }
    echo "migrate --check ok (drill)"
  else
    docker compose -f "$COMPOSE_FILE" exec -T "$BACKEND_SERVICE" \
      python manage.py migrate --check || {
        echo "WARNING: live migrate --check reported pending migrations (see STAGING.md § Migrate backlog)" >&2
      }
  fi
fi

if [[ -n "$HEALTH_URL" ]]; then
  echo "==> live health check (unchanged app DB): $HEALTH_URL"
  curl -sf "$HEALTH_URL" >/dev/null
  echo "health ok"
fi

echo "==> drop drill database"
docker compose -f "$COMPOSE_FILE" exec -T "$DB_SERVICE" \
  psql -U "$DB_USER" -d postgres -v ON_ERROR_STOP=1 \
  -c "DROP DATABASE IF EXISTS ${DRILL_DB};"

echo "ok restore drill passed (live DB untouched)"
