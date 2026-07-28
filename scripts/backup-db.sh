#!/usr/bin/env bash
# Hardened Postgres backup for Fast Plan (see DEPLOY.md §5, SECURITY.md).
# - custom-format dump (-Fc)
# - optional GPG encryption when BACKUP_GPG_RECIPIENT is set
# - retention cleanup
# - copies .env snapshot (mode 0600)
#
# Usage:
#   ROOT=/opt/fast_plan KEEP_DAYS=14 ./scripts/backup-db.sh
#   BACKUP_GPG_RECIPIENT=ops@example.com ./scripts/backup-db.sh

set -euo pipefail

ROOT="${ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
KEEP_DAYS="${KEEP_DAYS:-14}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"
DB_SERVICE="${DB_SERVICE:-db}"
DB_USER="${POSTGRES_USER:-fast_plan}"
DB_NAME="${POSTGRES_DB:-fast_plan}"
TS="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="${BACKUP_DIR:-$ROOT/backups}"

umask 077
mkdir -p "$BACKUP_DIR"
cd "$ROOT"

DUMP_PATH="$BACKUP_DIR/fast_plan_${TS}.dump"
docker compose -f "$COMPOSE_FILE" exec -T "$DB_SERVICE" \
  pg_dump -U "$DB_USER" -d "$DB_NAME" -Fc >"$DUMP_PATH"

if [[ ! -s "$DUMP_PATH" ]]; then
  echo "backup failed: empty dump" >&2
  rm -f "$DUMP_PATH"
  exit 1
fi

if [[ -n "${BACKUP_GPG_RECIPIENT:-}" ]]; then
  gpg --batch --yes --encrypt -r "$BACKUP_GPG_RECIPIENT" \
    --output "${DUMP_PATH}.gpg" "$DUMP_PATH"
  shred -u "$DUMP_PATH" 2>/dev/null || rm -f "$DUMP_PATH"
  DUMP_PATH="${DUMP_PATH}.gpg"
fi

if [[ -f "$ROOT/.env" ]]; then
  cp -a "$ROOT/.env" "$BACKUP_DIR/env_${TS}.bak"
  chmod 600 "$BACKUP_DIR/env_${TS}.bak"
fi

# media (optional volume) — best-effort tarball
if [[ -d "$ROOT/media" ]]; then
  tar -C "$ROOT" -czf "$BACKUP_DIR/media_${TS}.tar.gz" media
fi

find "$BACKUP_DIR" -name 'fast_plan_*.dump*' -mtime +"$KEEP_DAYS" -delete
find "$BACKUP_DIR" -name 'env_*.bak' -mtime +"$KEEP_DAYS" -delete
find "$BACKUP_DIR" -name 'media_*.tar.gz' -mtime +"$KEEP_DAYS" -delete

echo "ok $DUMP_PATH"
