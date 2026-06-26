#!/usr/bin/env bash
# Render production config and bring up the production stack.
#   scripts/prod/deploy.sh
set -euo pipefail
cd "$(dirname "$0")/../.."

[ -f .env.production ] || { echo "Missing .env.production (copy .env.production.example)"; exit 1; }
# shellcheck disable=SC1091
set -a; . ./.env.production; set +a

: "${DOMAIN:?set DOMAIN in .env.production}"
: "${MASTER_PASSWORD:?set MASTER_PASSWORD in .env.production}"

# Render nginx vhost (domain) and Odoo config (master password).
sed "s|__DOMAIN__|${DOMAIN}|g" \
  .docker/production/nginx/default.conf.template > .docker/production/nginx/default.conf
sed "s|__MASTER_PASSWORD__|${MASTER_PASSWORD}|g" \
  config/odoo.prod.conf.template > config/odoo.conf
echo "✓ rendered production config for ${DOMAIN}"

if ! docker compose -f docker-compose.prod.yml run --rm --entrypoint sh certbot \
      -c "[ -f /etc/letsencrypt/live/${DOMAIN}/fullchain.pem ]" 2>/dev/null; then
  echo "⚠ No certificate found for ${DOMAIN}. Run scripts/prod/issue-cert.sh first."
  exit 1
fi

echo "Starting production stack..."
docker compose -f docker-compose.prod.yml --env-file .env.production up -d
echo "✓ deployed. Create companies with:"
echo "    docker compose -f docker-compose.prod.yml run --rm web odoo -d <company> -i base,crm,sale_management,stock,purchase,account,hr,project,mrp,website --stop-after-init --without-demo=all"
echo "  Then browse https://<company>.${DOMAIN}"
