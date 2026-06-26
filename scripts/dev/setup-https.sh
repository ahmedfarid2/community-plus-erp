#!/usr/bin/env bash
# Generate a locally-trusted HTTPS certificate for *.odoo.local using mkcert,
# matching the project's house style (.docker/dev/nginx/certs).
#
#   brew install mkcert nss      # one-time
#   ./scripts/dev/setup-https.sh
set -euo pipefail
cd "$(dirname "$0")/../.."

CERTS=".docker/dev/nginx/certs"
mkdir -p "$CERTS"

if ! command -v mkcert >/dev/null 2>&1; then
  echo "mkcert not found. Install it first:  brew install mkcert nss"
  exit 1
fi

echo "Installing the local CA (mkcert -install)..."
mkcert -install

echo "Generating certificate for odoo.local + *.odoo.local ..."
mkcert -cert-file "$CERTS/odoo.local.pem" \
       -key-file  "$CERTS/odoo.local-key.pem" \
       odoo.local "*.odoo.local"

echo "✓ certs written to $CERTS"
echo ""
echo "Add the local domains to /etc/hosts (needs sudo). For example:"
echo "  sudo sh -c 'echo \"127.0.0.1 odoo.local acme.odoo.local globex.odoo.local\" >> /etc/hosts'"
echo ""
echo "Then:  ./scripts/start.sh   and open  https://acme.odoo.local"
