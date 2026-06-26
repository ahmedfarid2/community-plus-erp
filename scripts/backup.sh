#!/usr/bin/env bash
# Back up one company: PostgreSQL dump + filestore archive.
#   scripts/backup.sh <db_name>
# Output goes to backups/<db>-<timestamp>.{dump,filestore.tar.gz}
set -euo pipefail
cd "$(dirname "$0")/.."

DB="${1:-}"
[ -n "$DB" ] || { echo "Usage: scripts/backup.sh <db_name>"; exit 1; }
[[ "$DB" =~ ^[a-zA-Z0-9_]+$ ]] || { echo "Database name must be letters, digits, or underscore."; exit 1; }

ODOO_COMPOSE_FILE="${ODOO_COMPOSE_FILE:-docker-compose.yml}"
compose() {
  if [ -n "${ODOO_ENV_FILE:-}" ]; then
    docker compose -f "$ODOO_COMPOSE_FILE" --env-file "$ODOO_ENV_FILE" "$@"
  else
    docker compose -f "$ODOO_COMPOSE_FILE" "$@"
  fi
}

mkdir -p backups
STAMP="$(date +%Y%m%d-%H%M%S)"
DUMP="backups/${DB}-${STAMP}.dump"
FS="backups/${DB}-${STAMP}.filestore.tar.gz"

echo "Dumping database '$DB' ..."
compose exec -T db pg_dump -U odoo -Fc "$DB" > "$DUMP"

echo "Archiving filestore for '$DB' ..."
# Filestore may not exist yet for a brand-new DB; tolerate that.
compose exec -T web sh -c \
  "tar czf - -C /var/lib/odoo/filestore '$DB' 2>/dev/null || true" > "$FS"

echo "✓ backup complete:"
echo "    $DUMP"
echo "    $FS"
