#!/usr/bin/env bash
# Restore one company from a backup created by scripts/backup.sh.
#   scripts/restore.sh <new_db_name> <path/to/*.dump> [path/to/*.filestore.tar.gz]
# The target database must NOT already exist.
set -euo pipefail
cd "$(dirname "$0")/.."

DB="${1:-}"; DUMP="${2:-}"; FS="${3:-}"
[ -n "$DB" ] && [ -n "$DUMP" ] || {
  echo "Usage: scripts/restore.sh <new_db_name> <dump> [filestore.tar.gz]"; exit 1; }
[[ "$DB" =~ ^[a-zA-Z0-9_]+$ ]] || { echo "Database name must be letters, digits, or underscore."; exit 1; }
[ -f "$DUMP" ] || { echo "Dump not found: $DUMP"; exit 1; }

ODOO_COMPOSE_FILE="${ODOO_COMPOSE_FILE:-docker-compose.yml}"
compose() {
  if [ -n "${ODOO_ENV_FILE:-}" ]; then
    docker compose -f "$ODOO_COMPOSE_FILE" --env-file "$ODOO_ENV_FILE" "$@"
  else
    docker compose -f "$ODOO_COMPOSE_FILE" "$@"
  fi
}

echo "Creating empty database '$DB' ..."
compose exec -T db createdb -U odoo "$DB"

echo "Restoring data ..."
compose exec -T db pg_restore -U odoo --no-owner -d "$DB" < "$DUMP"

if [ -n "$FS" ] && [ -f "$FS" ]; then
  echo "Restoring filestore ..."
  compose exec -T web sh -c "mkdir -p /var/lib/odoo/filestore && tar xzf - -C /var/lib/odoo/filestore" < "$FS"
fi

echo "✓ restored as '$DB'. Restart Odoo if it is running:  scripts/stop.sh && scripts/start.sh"
echo "  Then open the database selector and pick '$DB'."
