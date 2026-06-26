#!/usr/bin/env bash
# Issue the wildcard Let's Encrypt certificate (DNS-01 via Cloudflare).
# Run ONCE before the first deploy; renewals happen automatically (certbot service).
#
# Prereqs: .env.production filled in, secrets/cloudflare.ini present (chmod 600),
# and the wildcard DNS record *.<DOMAIN> pointing at this server.
set -euo pipefail
cd "$(dirname "$0")/../.."

[ -f .env.production ] || { echo "Missing .env.production (copy .env.production.example)"; exit 1; }
[ -f secrets/cloudflare.ini ] || { echo "Missing secrets/cloudflare.ini (copy the .example)"; exit 1; }
# shellcheck disable=SC1091
set -a; . ./.env.production; set +a

echo "Requesting wildcard cert for ${DOMAIN} and *.${DOMAIN} ..."
docker compose -f docker-compose.prod.yml run --rm --entrypoint certbot certbot \
  certonly \
    --dns-cloudflare \
    --dns-cloudflare-credentials /run/secrets/cloudflare.ini \
    --dns-cloudflare-propagation-seconds 30 \
    -d "${DOMAIN}" -d "*.${DOMAIN}" \
    --agree-tos --non-interactive -m "${LETSENCRYPT_EMAIL}"

echo "✓ certificate issued into the 'letsencrypt' volume."
echo "  Now run: scripts/prod/deploy.sh"
