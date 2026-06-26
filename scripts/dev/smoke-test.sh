#!/usr/bin/env bash
# Local smoke test: log into a company over HTTP and read business data through
# the authenticated session. Exits non-zero if login fails or core data is empty.
#
#   scripts/dev/smoke-test.sh [db] [login] [password]
# Defaults: db=acme login=admin password=admin
set -eu   # no pipefail: a `grep` no-match in a pipe must yield 0, not abort
cd "$(dirname "$0")/../.."

DB="${1:-acme}"; LOGIN="${2:-admin}"; PASS="${3:-admin}"
BASE="http://localhost:${ODOO_PORT:-8069}"
[ -f .env ] && { set -a; . ./.env; set +a; BASE="http://localhost:${ODOO_PORT:-8069}"; }
CJ="$(mktemp)"; trap 'rm -f "$CJ"' EXIT
fail=0

jget() { grep -oE "\"$1\": ?[0-9]+" | grep -oE '[0-9]+' | head -1; }

echo "▶ Logging into '$DB' at $BASE as $LOGIN ..."
AUTH=$(curl -s -c "$CJ" -H 'Content-Type: application/json' \
  -d "{\"jsonrpc\":\"2.0\",\"params\":{\"db\":\"$DB\",\"login\":\"$LOGIN\",\"password\":\"$PASS\"}}" \
  "$BASE/web/session/authenticate")
OUID=$(echo "$AUTH" | jget uid)
if [ -z "${OUID:-}" ]; then
  echo "✗ LOGIN FAILED: $(echo "$AUTH" | grep -oE '"message": ?"[^"]*"' | head -1)"
  echo "  (If you see 'Database not found', restart Odoo: make restart)"
  exit 1
fi
echo "✓ login OK (uid=$OUID)"

check() { # label  model  domain  min
  local n
  n=$(curl -s -b "$CJ" -H 'Content-Type: application/json' \
    -d "{\"jsonrpc\":\"2.0\",\"params\":{\"model\":\"$2\",\"method\":\"search_count\",\"args\":[$3],\"kwargs\":{}}}" \
    "$BASE/web/dataset/call_kw" | jget result)
  n=${n:-0}
  if [ "$n" -ge "$4" ]; then printf "✓ %-26s %s\n" "$1" "$n"
  else printf "✗ %-26s %s (expected ≥ %s)\n" "$1" "$n" "$4"; fail=1; fi
}

check "Customers"            res.partner   '[["customer_rank",">",0]]' 1
check "Products"             product.template '[]'                     1
check "CRM opportunities"    crm.lead      '[]'                        1
check "Confirmed sales"      sale.order    '[["state","=","sale"]]'    1
check "Posted invoices"      account.move  '[["move_type","=","out_invoice"],["state","=","posted"]]' 1

# Optional modules — report only, never fail (a lighter company may lack them).
opt() {
  local n
  n=$(curl -s -b "$CJ" -H 'Content-Type: application/json' \
    -d "{\"jsonrpc\":\"2.0\",\"params\":{\"model\":\"$2\",\"method\":\"search_count\",\"args\":[[]],\"kwargs\":{}}}" \
    "$BASE/web/dataset/call_kw" | jget result)
  [ -n "${n:-}" ] && printf "· %-26s %s\n" "$1" "$n" || printf "· %-26s (app not installed)\n" "$1"
}
opt "Purchase orders" purchase.order
opt "Employees"       hr.employee

echo "------------------------------------------"
[ "$fail" -eq 0 ] && echo "PASS — '$DB' is healthy and populated." || { echo "FAIL — see ✗ above."; exit 1; }
