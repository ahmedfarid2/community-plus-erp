#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

DB_NAME="${ONESUITE_DB:-onesuite}"
ENV_FILE=".env.cpanel"
COMPOSE_FILE="docker-compose.cpanel.yml"

if command -v podman-compose >/dev/null 2>&1; then
  COMPOSE=(podman-compose -f "$COMPOSE_FILE")
  RUNTIME="podman"
elif command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  COMPOSE=(docker compose -f "$COMPOSE_FILE")
  RUNTIME="docker"
else
  echo "[ERROR] Neither podman-compose nor docker compose is available."
  exit 1
fi

if [ ! -f "$ENV_FILE" ]; then
  command -v openssl >/dev/null 2>&1 || { echo "[ERROR] openssl is required to generate secrets."; exit 1; }
  umask 077
  cat > "$ENV_FILE" <<EOF
ODOO_TAG=19.0
PG_TAG=16
ONESUITE_DB=onesuite
ONESUITE_HTTP_PORT=18069
ONESUITE_CHAT_PORT=18072
POSTGRES_PASSWORD=$(openssl rand -hex 32)
MASTER_PASSWORD=$(openssl rand -hex 32)
ADMIN_PASSWORD=$(openssl rand -hex 18)
EOF
  chmod 600 "$ENV_FILE"
  echo "[PASS] Generated $ENV_FILE with strong local secrets."
fi

set -a
# shellcheck disable=SC1090
. "./$ENV_FILE"
set +a
DB_NAME="${ONESUITE_DB:-onesuite}"

for required in POSTGRES_PASSWORD MASTER_PASSWORD ADMIN_PASSWORD; do
  [ -n "${!required:-}" ] || { echo "[ERROR] $required is empty in $ENV_FILE"; exit 1; }
done

# Do not collide with another live Odoo stack.
if curl -fsS "http://127.0.0.1:${ONESUITE_HTTP_PORT:-18069}/web/login" >/dev/null 2>&1; then
  if ! ${COMPOSE[@]} ps 2>/dev/null | grep -q "onesuite-nextgen-web"; then
    echo "[STOP] Port ${ONESUITE_HTTP_PORT:-18069} already serves another Odoo instance."
    echo "Run: bash scripts/cpanel/audit.sh"
    echo "This deploy script will not overwrite or stop an unknown existing system."
    exit 20
  fi
fi

sed "s|__MASTER_PASSWORD__|${MASTER_PASSWORD}|g"   config/odoo.cpanel.conf.template > config/odoo.conf
chmod 600 config/odoo.conf

echo "======================================================================"
echo " ONESUITE - CPANEL DEPLOY"
echo " Runtime   : $RUNTIME"
echo " Database  : $DB_NAME"
echo " HTTP      : 127.0.0.1:${ONESUITE_HTTP_PORT:-18069}"
echo " Websocket : 127.0.0.1:${ONESUITE_CHAT_PORT:-18072}"
echo "======================================================================"

echo
echo "=== 1. Build OneSuite image ==="
${COMPOSE[@]} build web

echo
echo "=== 2. Start PostgreSQL ==="
${COMPOSE[@]} up -d db

echo "Waiting for PostgreSQL..."
for i in $(seq 1 60); do
  if ${COMPOSE[@]} exec -T db pg_isready -U odoo -d postgres >/dev/null 2>&1; then
    echo "[PASS] PostgreSQL ready."
    break
  fi
  [ "$i" -eq 60 ] && { echo "[ERROR] PostgreSQL did not become ready."; exit 1; }
  sleep 2
done

echo
echo "=== 3. Install/upgrade OneSuite database ==="
${COMPOSE[@]} run --rm web   odoo -d "$DB_NAME"   -i community_plus_sme_trading,onesuite_hub   -u community_plus_theme,dashboards_lite,onesuite_hub   --stop-after-init --without-demo=all

echo
echo "=== 4. Apply NextGen identity and secure admin ==="
${COMPOSE[@]} run --rm --no-deps -T   -e ONESUITE_ADMIN_PASSWORD="$ADMIN_PASSWORD"   web odoo shell -d "$DB_NAME" --no-http <<'PY'
import os
company = env.ref("base.main_company")
country = env["res.country"].search([("code", "=", "PG")], limit=1)
vals = {
    "name": "NextGen Technology PNG Limited",
    "email": "info@nextgenpng.net",
}
if country:
    vals["country_id"] = country.id
company.write(vals)

admin = env.ref("base.user_admin")
admin.write({
    "name": "OneSuite Administrator",
    "login": "admin",
    "password": os.environ["ONESUITE_ADMIN_PASSWORD"],
})
env.cr.commit()
print("Company:", company.name)
print("Admin login: admin")
PY

echo
echo "=== 5. Start Odoo ==="
${COMPOSE[@]} up -d web

echo "Waiting for Odoo..."
for i in $(seq 1 90); do
  code="$(curl -sS -o /dev/null -w '%{http_code}' "http://127.0.0.1:${ONESUITE_HTTP_PORT:-18069}/web/login" || true)"
  if [ "$code" = "200" ] || [ "$code" = "303" ]; then
    echo "[PASS] Odoo reachable (HTTP $code)."
    break
  fi
  [ "$i" -eq 90 ] && {
    echo "[ERROR] Odoo did not become reachable."
    ${COMPOSE[@]} logs --tail=120 web || true
    exit 1
  }
  sleep 2
done

echo
echo "=== 6. Final status ==="
${COMPOSE[@]} ps

echo
echo "======================================================================"
echo " ONESUITE BACKEND READY"
echo " Public domain : https://onesuite.nextgenpng.net"
echo " Local backend : http://127.0.0.1:${ONESUITE_HTTP_PORT:-18069}"
echo " Admin login   : admin"
echo " Admin password: stored in $ENV_FILE as ADMIN_PASSWORD"
echo
echo "NEXT: configure the cPanel Apache reverse proxy:"
echo "      sudo bash scripts/cpanel/apache-proxy-root.sh"
echo "======================================================================"
