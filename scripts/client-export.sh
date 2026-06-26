#!/usr/bin/env bash
# Export a client database, filestore, and small metadata manifest.
#
#   scripts/client-export.sh <db_name>
set -euo pipefail
cd "$(dirname "$0")/.."

DB="${1:-}"
[ -n "$DB" ] || { echo "Usage: scripts/client-export.sh <db_name>"; exit 1; }
[[ "$DB" =~ ^[a-zA-Z0-9_]+$ ]] || { echo "Database name must be letters, digits, or underscore."; exit 1; }

STAMP="$(date +%Y%m%d-%H%M%S)"
MANIFEST="backups/${DB}-${STAMP}.manifest.txt"

./scripts/backup.sh "$DB"

{
  echo "database=$DB"
  echo "exported_at=$STAMP"
  echo "product=Odoo Community Plus ERP"
  echo "pack=sme_trading"
  echo "policy=Native Community + audited open-source addons + custom clean-room modules"
} > "$MANIFEST"

echo "✓ export manifest:"
echo "    $MANIFEST"
