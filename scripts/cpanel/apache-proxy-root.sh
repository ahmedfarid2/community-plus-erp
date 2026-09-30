#!/usr/bin/env bash
set -Eeuo pipefail

[ "$(id -u)" -eq 0 ] || { echo "[ERROR] Run this script as root."; exit 1; }

USER_NAME="nextgenpng"
DOMAIN="onesuite.nextgenpng.net"
BACKEND="http://127.0.0.1:18069"
WS_BACKEND="ws://127.0.0.1:18072"

STD="/etc/apache2/conf.d/userdata/std/2_4/$USER_NAME/$DOMAIN"
SSL="/etc/apache2/conf.d/userdata/ssl/2_4/$USER_NAME/$DOMAIN"

mkdir -p "$STD" "$SSL"

write_proxy() {
  local file="$1"
  cat > "$file" <<EOF
# OneSuite -> local Odoo 19 backend.
# Managed by community-plus-erp/scripts/cpanel/apache-proxy-root.sh

ProxyPreserveHost On
ProxyRequests Off

ProxyPass        /websocket  $WS_BACKEND/websocket retry=0 timeout=600
ProxyPassReverse /websocket  $WS_BACKEND/websocket

ProxyPass        /  $BACKEND/ retry=0 timeout=600
ProxyPassReverse /  $BACKEND/

RequestHeader set X-Forwarded-Proto "https"
RequestHeader set X-Forwarded-Port "443"
EOF
}

write_proxy "$STD/onesuite_proxy.conf"
write_proxy "$SSL/onesuite_proxy.conf"

if command -v /scripts/rebuildhttpdconf >/dev/null 2>&1; then
  /scripts/rebuildhttpdconf
fi

apachectl configtest
if command -v systemctl >/dev/null 2>&1; then
  systemctl reload httpd
else
  service httpd reload
fi

echo "[PASS] Apache proxy enabled for https://$DOMAIN -> $BACKEND"
