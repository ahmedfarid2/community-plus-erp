#!/usr/bin/env bash
# Install every Community application a company could need into a database.
# Dynamically selects all real apps (application=True) and SKIPS Odoo's
# Enterprise-only upsell modules (to_buy=True, e.g. accountant/helpdesk/sign).
# Idempotent: only installs what's still missing.
#
#   scripts/dev/install-all-apps.sh <db>
set -euo pipefail
cd "$(dirname "$0")/../.."

DB="${1:-}"
[ -n "$DB" ] || { echo "Usage: scripts/dev/install-all-apps.sh <db>"; exit 1; }

MODS=$(docker compose exec -T db psql -U odoo -d "$DB" -tAc \
  "SELECT string_agg(name, ',') FROM ir_module_module
   WHERE application = true AND to_buy = false AND state = 'uninstalled';" 2>/dev/null | tr -d '[:space:]')

if [ -z "$MODS" ]; then
  echo "✓ $DB already has every Community app installed."
  exit 0
fi

echo "Installing into '$DB':"
echo "  $MODS" | tr ',' '\n' | sed 's/^/    - /'
echo "(this pulls many dependencies — a few minutes)"
docker compose run --rm --no-deps web odoo -d "$DB" -i "$MODS" --stop-after-init --without-demo=all
echo "✓ done. Restart Odoo to load the new apps:  make restart"
