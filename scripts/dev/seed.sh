#!/usr/bin/env bash
# Seed realistic demo data into a company database (idempotent).
#   scripts/dev/seed.sh <db> [--reset]
# --reset removes previously seeded SEED-* records first.
# Tune volumes with env vars, e.g.:  SEED_CUSTOMERS=50 SEED_SALES=40 scripts/dev/seed.sh acme
set -euo pipefail
cd "$(dirname "$0")/../.."

DB="${1:-}"
[ -n "$DB" ] || { echo "Usage: scripts/dev/seed.sh <db> [--reset]"; exit 1; }
[ "${2:-}" = "--reset" ] && export SEED_RESET=1

echo "Seeding database '$DB' (this loads the demo records)..."
docker compose run --rm --no-deps -T \
  -e SEED_RESET="${SEED_RESET:-}" \
  -e SEED_CUSTOMERS="${SEED_CUSTOMERS:-}" -e SEED_VENDORS="${SEED_VENDORS:-}" \
  -e SEED_PRODUCTS="${SEED_PRODUCTS:-}"   -e SEED_SALES="${SEED_SALES:-}" \
  -e SEED_PURCHASES="${SEED_PURCHASES:-}" -e SEED_LEADS="${SEED_LEADS:-}" \
  web odoo shell -d "$DB" --no-http < scripts/dev/seed.py
