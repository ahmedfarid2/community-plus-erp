#!/usr/bin/env bash
# Stop the stack. Data is kept in named volumes (odoo-db-data, odoo-web-data).
# Pass --wipe to ALSO delete all data volumes (destroys every company!).
set -euo pipefail
cd "$(dirname "$0")/.."

if [ "${1:-}" = "--wipe" ]; then
  read -r -p "This deletes ALL company data. Type 'yes' to confirm: " ans
  [ "$ans" = "yes" ] || { echo "Aborted."; exit 1; }
  docker compose down -v
  echo "✓ stopped and wiped all volumes"
else
  docker compose down
  echo "✓ stopped (data preserved). Restart with scripts/start.sh"
fi
