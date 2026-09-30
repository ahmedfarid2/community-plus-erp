#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

ENV_FILE=".env.cpanel"
COMPOSE_FILE="docker-compose.cpanel.yml"

# The checkout may live inside a cPanel document root. Protect source, secrets,
# scripts, configs and Git metadata until Apache is switched to reverse proxy.
HTACCESS=".htaccess"
if [ -f "$HTACCESS" ] && ! grep -q "BEGIN ONESUITE SOURCE PROTECTION" "$HTACCESS"; then
  cp -p "$HTACCESS" "$HTACCESS.pre_onesuite_$(date +%Y%m%d_%H%M%S).bak"
  cat >> "$HTACCESS" <<'HT'
# BEGIN ONESUITE SOURCE PROTECTION
<IfModule mod_rewrite.c>
RewriteEngine On
RewriteRule ^(?:\.git|addons|config|docker|docs|scripts|secrets|backups)(?:/|$) - [F,L,NC]
RewriteRule ^(?:\.env(?:\..*)?|docker-compose.*|Makefile)$ - [F,L,NC]
</IfModule>
<FilesMatch "(?i)^(?:\.env.*|docker-compose.*|Makefile)$">
  Require all denied
</FilesMatch>
# END ONESUITE SOURCE PROTECTION
HT
  echo "[PASS] Protected OneSuite source/secrets in cPanel document root."
fi

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

if curl -fsS "http://127.0.0.1:${ONESUITE_HTTP_PORT:-18069}/web/login" >/dev/null 2>&1; then
  if ! ${COMPOSE[@]} ps 2>/dev/null | grep -q "onesuite-nextgen-web"; then
    echo "[STOP] Port ${ONESUITE_HTTP_PORT:-18069} already serves another Odoo instance."
    echo "Run: bash scripts/cpanel/audit.sh"
    echo "This deploy script will not overwrite or stop an unknown existing system."
    exit 20
  fi
fi

sed   -e "s|__MASTER_PASSWORD__|${MASTER_PASSWORD}|g"   -e "s|__DB_NAME__|${DB_NAME}|g"   config/odoo.cpanel.conf.template > config/odoo.conf
chmod 600 config/odoo.conf

echo "======================================================================"
echo " ONESUITE - CPANEL DEPLOY"
echo " Runtime   : $RUNTIME"
echo " Database  : $DB_NAME"
echo " HTTP      : 127.0.0.1:${ONESUITE_HTTP_PORT:-18069}"
echo " Websocket : 127.0.0.1:${ONESUITE_CHAT_PORT:-18072}"
echo "======================================================================"

echo
echo "=== 1. Fetch Community dependencies ==="
bash scripts/dev/fetch-thirdparty.sh

echo
echo "=== 2. Build OneSuite Odoo 19 image ==="
${COMPOSE[@]} build web

echo
echo "=== 3. Start PostgreSQL ==="
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

CUSTOM_MODULES="onesuite_nextgen_pack,community_plus_sme_trading,community_plus_theme,dashboards_lite,onesuite_hub,payment_plan_core,payment_plan_account,payment_plan_reports,smart_approval_workflow,smart_approval_purchase,smart_approval_account,smart_approval_sale,smart_approval_inventory,smart_approval_hr,smart_approval_payment_plan,smart_cpq_builder,smart_cpq_sale,smart_cpq_approval_workflow,smart_subscription_manager,smart_subscription_account,smart_subscription_approval,smart_field_service_suite,smart_fsm_account,smart_fsm_approval_workflow,advanced_procurement_suite,advanced_procurement_purchase,advanced_procurement_approval_workflow,advanced_inventory_optimization,advanced_inventory_purchase,advanced_inventory_procurement,advanced_inventory_approval_workflow"

echo
echo "=== 4. Install/upgrade complete NextGen OneSuite pack ==="
${COMPOSE[@]} run --rm web   odoo -d "$DB_NAME"   -i onesuite_nextgen_pack   -u "$CUSTOM_MODULES"   --workers=0   --stop-after-init   --without-demo=all

echo
echo "=== 5. Apply NextGen identity and secure admin ==="
${COMPOSE[@]} run --rm --no-deps -T   -e ONESUITE_ADMIN_PASSWORD="$ADMIN_PASSWORD"   web odoo shell -d "$DB_NAME" --no-http --workers=0 <<'PY'
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

params = env["ir.config_parameter"].sudo()
params.set_param("web.base.url", "https://onesuite.nextgenpng.net")
params.set_param("web.base.url.freeze", "True")

env.cr.commit()
print("Company:", company.name)
print("Admin login: admin")
print("Base URL: https://onesuite.nextgenpng.net")
PY

echo
echo "=== 6. Start Odoo ==="
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
    ${COMPOSE[@]} logs --tail=160 web || true
    exit 1
  }
  sleep 2
done

echo
echo "=== 7. Final status ==="
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
