#!/usr/bin/env bash
# Create a new company on Odoo.
#
#   scripts/new-company.sh <name> [modules]      # default: new DB on shared instance
#   scripts/new-company.sh <name> --isolated     # full separate stack (own port/volumes)
#
# <name>    company database name (letters, digits, underscore). e.g. acme
# [modules] comma list of apps to pre-install. Default = the full standard suite.
#
# Multi-database mode (default): adds a new Odoo database to the running instance.
# The new admin login is  admin / admin  — change it on first login.
set -euo pipefail
cd "$(dirname "$0")/.."

NAME="${1:-}"
[ -n "$NAME" ] || { echo "Usage: scripts/new-company.sh <name> [modules|--isolated]"; exit 1; }
[[ "$NAME" =~ ^[a-zA-Z0-9_]+$ ]] || { echo "Name must be letters/digits/underscore."; exit 1; }

# shellcheck disable=SC1091
set -a; . ./.env; set +a

DEFAULT_MODULES="base,crm,sale_management,stock,purchase,account,hr,project,mrp,website,account_financial_reports_lite"

# ── Isolated full-stack mode ───────────────────────────────────────────────
if [ "${2:-}" = "--isolated" ]; then
  DIR="companies/$NAME"
  PORT=$(( ${ODOO_PORT:-8069} + RANDOM % 1000 + 100 ))
  mkdir -p "$DIR/config" "$DIR/addons"
  sed "s|__MASTER_PASSWORD__|${MASTER_PASSWORD:-change-me-master}|g" \
    config/odoo.conf.template > "$DIR/config/odoo.conf"
  cat > "$DIR/docker-compose.yml" <<YAML
services:
  db:
    image: postgres:${PG_TAG:-16}
    environment:
      POSTGRES_USER: odoo
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-odoo}
      POSTGRES_DB: postgres
    volumes: [ "db:/var/lib/postgresql/data" ]
    healthcheck:
      test: ["CMD","pg_isready","-U","odoo"]
      interval: 5s
      timeout: 5s
      retries: 12
  web:
    image: odoo:${ODOO_TAG:-19.0}
    depends_on:
      db: { condition: service_healthy }
    ports: [ "${PORT}:8069" ]
    environment: { HOST: db, USER: odoo, PASSWORD: ${POSTGRES_PASSWORD:-odoo} }
    volumes:
      - "web:/var/lib/odoo"
      - "./config:/etc/odoo"
      - "./addons:/mnt/extra-addons"
volumes: { db: {}, web: {} }
YAML
  ( cd "$DIR" && docker compose -p "odoo_$NAME" up -d )
  echo "✓ isolated stack '$NAME' starting → http://localhost:${PORT}"
  echo "  Create its database in the web UI (master password from .env)."
  exit 0
fi

# ── Multi-database mode (default) ──────────────────────────────────────────
MODULES="${2:-$DEFAULT_MODULES}"
echo "Creating company database '$NAME' with modules: $MODULES"
echo "(first run installs many apps — this can take a few minutes)"
docker compose run --rm web \
  odoo -d "$NAME" -i "$MODULES" --stop-after-init --without-demo=all
echo "✓ company '$NAME' created."
echo "  Direct:    http://localhost:${ODOO_PORT:-8069}  →  select database '$NAME'"
echo "  Subdomain: https://${NAME}.odoo.local  (run 'make https' once, then add to /etc/hosts:)"
echo "             sudo sh -c 'echo \"127.0.0.1 ${NAME}.odoo.local\" >> /etc/hosts'"
echo "  Login: admin / admin   (change the password immediately)"
