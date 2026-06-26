#!/usr/bin/env bash
# Start the Odoo stack: render odoo.conf from .env, then docker compose up.
set -euo pipefail
cd "$(dirname "$0")/.."

[ -f .env ] || { echo "No .env found. Run: cp .env.example .env"; exit 1; }
# shellcheck disable=SC1091
set -a; . ./.env; set +a

# Render config/odoo.conf from the template, injecting the master password.
sed "s|__MASTER_PASSWORD__|${MASTER_PASSWORD:-change-me-master}|g" \
  config/odoo.conf.template > config/odoo.conf
echo "✓ rendered config/odoo.conf"

echo "Pulling images and starting containers..."
docker compose up -d

echo "Waiting for Odoo to become reachable on http://localhost:${ODOO_PORT:-8069} ..."
for i in $(seq 1 60); do
  if curl -sf "http://localhost:${ODOO_PORT:-8069}/web/database/selector" >/dev/null 2>&1; then
    echo "✓ Odoo is up → http://localhost:${ODOO_PORT:-8069}"
    exit 0
  fi
  sleep 2
done
echo "Odoo did not respond in time. Check logs: docker compose logs -f web"
exit 1
