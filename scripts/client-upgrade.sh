#!/usr/bin/env bash
# Upgrade the Community Plus pack and custom modules in a client database.
#
#   scripts/client-upgrade.sh <db_name>
set -euo pipefail
cd "$(dirname "$0")/.."

DB="${1:-}"
[ -n "$DB" ] || { echo "Usage: scripts/client-upgrade.sh <db_name>"; exit 1; }
[[ "$DB" =~ ^[a-zA-Z0-9_]+$ ]] || { echo "Database name must be letters, digits, or underscore."; exit 1; }

[ -z "${ODOO_ENV_FILE:-}" ] && [ -f .env ] && { set -a; . ./.env; set +a; }

ODOO_COMPOSE_FILE="${ODOO_COMPOSE_FILE:-docker-compose.yml}"
compose() {
  if [ -n "${ODOO_ENV_FILE:-}" ]; then
    docker compose -f "$ODOO_COMPOSE_FILE" --env-file "$ODOO_ENV_FILE" "$@"
  else
    docker compose -f "$ODOO_COMPOSE_FILE" "$@"
  fi
}

MODULES="community_plus_sme_trading,account_loan_lite"
echo "Upgrading $MODULES in '$DB' ..."
compose run --rm --no-deps web \
  odoo -d "$DB" -u "$MODULES" --stop-after-init --without-demo=all

echo "✓ upgrade complete. Restart Odoo, then run: make client-health db=$DB"
