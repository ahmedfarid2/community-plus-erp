#!/usr/bin/env bash
# Back up every non-template production client database.
# Intended for cron/systemd timers on the production host.
set -euo pipefail
cd "$(dirname "$0")/../.."

export ODOO_COMPOSE_FILE="${ODOO_COMPOSE_FILE:-docker-compose.prod.yml}"
export ODOO_ENV_FILE="${ODOO_ENV_FILE:-.env.production}"

compose() {
  docker compose -f "$ODOO_COMPOSE_FILE" --env-file "$ODOO_ENV_FILE" "$@"
}

mapfile -t DBS < <(compose exec -T db psql -U odoo -d postgres -tAc \
  "SELECT datname FROM pg_database
   WHERE datistemplate = false
     AND datname NOT IN ('postgres')
   ORDER BY datname;")

if [ "${#DBS[@]}" -eq 0 ]; then
  echo "No client databases found."
  exit 0
fi

for db in "${DBS[@]}"; do
  [ -n "$db" ] || continue
  echo "==> Backing up $db"
  ./scripts/backup.sh "$db"
done

echo "✓ all production client backups complete"
