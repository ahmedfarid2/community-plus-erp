#!/usr/bin/env bash
# Check that a Community Plus client database exists and has the pack installed.
#
#   scripts/client-health.sh <db_name>
set -euo pipefail
cd "$(dirname "$0")/.."

DB="${1:-}"
[ -n "$DB" ] || { echo "Usage: scripts/client-health.sh <db_name>"; exit 1; }
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

fail=0

echo "Checking database '$DB' ..."
if compose exec -T db psql -U odoo -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = '$DB'" | grep -q 1; then
  echo "✓ database exists"
else
  echo "✗ database does not exist"
  exit 1
fi

echo "Checking Community Plus pack ..."
STATE="$(compose exec -T db psql -U odoo -d "$DB" -tAc "SELECT state FROM ir_module_module WHERE name = 'community_plus_sme_trading'" 2>/dev/null | tr -d '[:space:]' || true)"
if [ "$STATE" = "installed" ]; then
  echo "✓ community_plus_sme_trading installed"
else
  echo "✗ community_plus_sme_trading state: ${STATE:-missing}"
  fail=1
fi

mkdir -p backups
if [ -w backups ]; then
  echo "✓ backups directory writable"
else
  echo "✗ backups directory is not writable"
  fail=1
fi

BASE="http://localhost:${ODOO_PORT:-8069}"
if curl -sf "$BASE/web/database/selector" >/dev/null 2>&1; then
  echo "✓ Odoo HTTP endpoint reachable at $BASE"
  if [ "${CLIENT_HEALTH_DEEP:-0}" = "1" ]; then
    echo "Checking deep seeded data smoke test ..."
    ./scripts/dev/smoke-test.sh "$DB" || fail=1
  else
    echo "· skipped deep seeded data smoke test; run CLIENT_HEALTH_DEEP=1 make client-health db=$DB after seeding"
  fi
else
  echo "· Odoo HTTP endpoint is not reachable at $BASE; skipped live smoke test"
fi

[ "$fail" -eq 0 ] && echo "PASS — '$DB' is ready." || { echo "FAIL — '$DB' needs attention."; exit 1; }
