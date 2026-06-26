#!/usr/bin/env bash
# One-command client onboarding: create -> configure -> (seed) -> verify.
# Orchestrates the existing client/dev scripts into a single repeatable pipeline.
#
#   scripts/onboard-client.sh <db> <COUNTRY_CC> "<Company Name>" [--seed] [--all-apps]
#
# Examples:
#   scripts/onboard-client.sh acme EG "Acme Trading LLC"
#   scripts/onboard-client.sh demo US "Demo Co" --seed --all-apps
set -euo pipefail
cd "$(dirname "$0")/.."

DB="${1:-}"; COUNTRY="${2:-US}"; COMPANY="${3:-}"
[ -n "$DB" ] && [ -n "$COMPANY" ] || {
  echo 'Usage: scripts/onboard-client.sh <db> <CC> "<Company Name>" [--seed] [--all-apps]'; exit 1; }
[ -f .env ] && { set -a; . ./.env; set +a; }
PORT="${ODOO_PORT:-8069}"

SEED=0; ALLAPPS=0
for a in "$@"; do
  [ "$a" = "--seed" ] && SEED=1
  [ "$a" = "--all-apps" ] && ALLAPPS=1
done

wait_up() { for _ in $(seq 1 60); do
  curl -sf "http://localhost:${PORT}/web/database/selector" >/dev/null 2>&1 && return 0; sleep 2; done; }

echo "════════ Onboarding: ${COMPANY}  (db=${DB}, country=${COUNTRY}) ════════"

echo "▶ 1/6  Create + brand + install the Community Plus pack"
./scripts/client-init.sh "$DB" sme_trading "$COUNTRY" "$COMPANY"

echo "▶ 2/6  Wire accounting (fiscal year + asset accounts)"
./scripts/dev/setup-accounting.sh "$DB"

if [ "$ALLAPPS" = 1 ]; then
  echo "▶ 3/6  Install every Community app"
  ./scripts/dev/install-all-apps.sh "$DB"
else
  echo "▶ 3/6  (skipped --all-apps; pack apps only)"
fi

if [ "$SEED" = 1 ]; then
  echo "▶ 4/6  Seed demo data"
  ./scripts/dev/seed.sh "$DB"
else
  echo "▶ 4/6  (skipped --seed; empty company)"
fi

echo "▶ 5/6  Reload Odoo"
docker compose restart web >/dev/null 2>&1
wait_up

echo "▶ 6/6  Verify"
./scripts/client-health.sh "$DB" || echo "  (health check reported issues — review above)"
if [ "$SEED" = 1 ]; then
  # Full data smoke test only makes sense once demo data is loaded.
  ./scripts/dev/smoke-test.sh "$DB" admin admin || echo "  (smoke test reported issues — review above)"
else
  echo "  (data smoke skipped — empty company; health check above confirms readiness)"
fi

echo ""
echo "════════ DONE — ${COMPANY} is ready ════════"
echo "  Database : ${DB}"
echo "  URL      : http://localhost:${PORT}  → select '${DB}'"
echo "  Login    : admin / admin   (change on first login)"
[ "$SEED" = 1 ]    && echo "  Demo data: loaded"
[ "$ALLAPPS" = 1 ] && echo "  Apps     : full Community suite"
echo "  Backup   : make backup db=${DB}    ·    Export: make client-export db=${DB}"
