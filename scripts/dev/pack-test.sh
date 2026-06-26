#!/usr/bin/env bash
# Fresh-database install test for the Community Plus pack.
# Creates a throwaway DB, installs community_plus_sme_trading (pulling every
# dependency incl. the custom *_lite modules), checks the log for errors and
# verifies the key modules ended up 'installed', then drops the DB.
#
#   scripts/dev/pack-test.sh [--keep]   # --keep leaves the DB for inspection
set -euo pipefail
cd "$(dirname "$0")/../.."

DB="packtest"
PACK="community_plus_sme_trading"
KEEP="${1:-}"
LOG="$(mktemp)"

drop_db() {
  docker compose exec -T db psql -U odoo -d postgres -tAc \
    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity
     WHERE datname='$DB' AND pid <> pg_backend_pid();" >/dev/null 2>&1 || true
  docker compose exec -T db dropdb -U odoo --if-exists "$DB" >/dev/null 2>&1 || true
}

fail() { echo "✗ $1"; [ "$KEEP" = "--keep" ] || drop_db; rm -f "$LOG"; exit 1; }

echo "▶ Fresh-DB install test for '$PACK' (db: $DB)"
drop_db   # remove any leftover from a previous run

echo "  installing into a clean database (this pulls all dependencies)..."
docker compose run --rm --no-deps web odoo -d "$DB" -i "$PACK" \
  --stop-after-init --without-demo=all >"$LOG" 2>&1 || fail "odoo install command failed"

grep -qiE "Registry loaded" "$LOG" || fail "install did not finish (no 'Registry loaded')"
if grep -qiE " ERROR | CRITICAL |Traceback" "$LOG"; then
  echo "  --- errors found ---"; grep -iE "ERROR|CRITICAL|Traceback" "$LOG" | head -8
  fail "errors during install"
fi

echo "  verifying module states..."
NOTREADY=$(docker compose exec -T db psql -U odoo -d "$DB" -tAc \
  "SELECT string_agg(name || '=' || state, ', ')
   FROM ir_module_module
   WHERE name IN ('$PACK','account_loan_lite','account_deferred_lite','account_review_lite',
                  'account_financial_reports_lite','business_approvals_lite','documents_lite',
                  'helpdesk_lite','subscriptions_lite')
   AND state <> 'installed';" 2>/dev/null | tr -d '[:space:]')
[ -z "$NOTREADY" ] || fail "modules not installed: $NOTREADY"

COUNT=$(docker compose exec -T db psql -U odoo -d "$DB" -tAc \
  "SELECT count(*) FROM ir_module_module WHERE state='installed';" 2>/dev/null | tr -d '[:space:]')
echo "✓ pack installed cleanly — $COUNT modules, all key modules present"

if [ "$KEEP" = "--keep" ]; then echo "  (kept '$DB' for inspection)"; else drop_db; echo "  (dropped '$DB')"; fi
rm -f "$LOG"
echo "PASS — '$PACK' installs on a fresh database."
