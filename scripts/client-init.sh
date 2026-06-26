#!/usr/bin/env bash
# Create and initialize a sellable Community Plus client database.
#
#   scripts/client-init.sh <db_name> [pack] [country_code] [company_name]
#   scripts/client-init.sh acme sme_trading EG "Acme Trading LLC"
set -euo pipefail
cd "$(dirname "$0")/.."

DB="${1:-}"
PACK="${2:-sme_trading}"
COUNTRY="${3:-EG}"
COMPANY_NAME="${4:-$DB}"

[ -n "$DB" ] || { echo "Usage: scripts/client-init.sh <db_name> [pack] [country_code] [company_name]"; exit 1; }
[[ "$DB" =~ ^[a-zA-Z0-9_]+$ ]] || { echo "Database name must be letters, digits, or underscore."; exit 1; }

case "$PACK" in
  sme_trading) MODULE="community_plus_sme_trading" ;;
  *) echo "Unknown pack '$PACK'. Supported packs: sme_trading"; exit 1 ;;
esac

[ -z "${ODOO_ENV_FILE:-}" ] && [ -f .env ] && { set -a; . ./.env; set +a; }

ODOO_COMPOSE_FILE="${ODOO_COMPOSE_FILE:-docker-compose.yml}"
compose() {
  if [ -n "${ODOO_ENV_FILE:-}" ]; then
    docker compose -f "$ODOO_COMPOSE_FILE" --env-file "$ODOO_ENV_FILE" "$@"
  else
    docker compose -f "$ODOO_COMPOSE_FILE" "$@"
  fi
}

echo "Creating Community Plus client '$DB' with pack '$PACK' ..."
compose run --rm web \
  odoo -d "$DB" -i "$MODULE" --stop-after-init --without-demo=all

echo "Applying company identity ..."
./scripts/dev/brand-company.sh "$DB" "$COMPANY_NAME" "$COUNTRY"

echo "Running health check ..."
./scripts/client-health.sh "$DB" || {
  echo "Client was created, but the live health check could not complete."
  echo "Start/restart Odoo and run: make client-health db=$DB"
}

echo "✓ Community Plus client '$DB' initialized."
