#!/usr/bin/env bash
set -u

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

echo "======================================================================"
echo " ONESUITE - CPANEL READ-ONLY PREDEPLOY AUDIT"
echo "======================================================================"
echo "User      : $(whoami)"
echo "Host      : $(hostname -f 2>/dev/null || hostname)"
echo "Directory : $ROOT"
echo

echo "=== Runtime ==="
command -v podman || true
podman --version 2>/dev/null || true
command -v podman-compose || true
podman-compose --version 2>/dev/null || true
command -v docker || true
docker --version 2>/dev/null || true
echo

echo "=== Existing OneSuite/Odoo containers ==="
podman ps -a --format '{{.Names}} {{.Status}} {{.Ports}}' 2>/dev/null | grep -Ei 'odoo|onesuite|postgres' || true
docker ps -a --format '{{.Names}} {{.Status}} {{.Ports}}' 2>/dev/null | grep -Ei 'odoo|onesuite|postgres' || true
echo

echo "=== Existing related volumes ==="
podman volume ls 2>/dev/null | grep -Ei 'odoo|onesuite' || true
docker volume ls 2>/dev/null | grep -Ei 'odoo|onesuite' || true
echo

echo "=== Required local ports ==="
for p in 18069 18072; do
  echo "-- port $p"
  (ss -ltnp 2>/dev/null || netstat -ltnp 2>/dev/null || true) | grep -E "[:.]$p[[:space:]]" || echo "FREE"
done
echo

echo "=== Domain backend probe ==="
curl -sS -o /dev/null -w '127.0.0.1:18069 -> HTTP %{http_code}\n' http://127.0.0.1:18069/web/login 2>/dev/null || true
curl -sS -o /dev/null -w 'https://onesuite.nextgenpng.net -> HTTP %{http_code}\n' https://onesuite.nextgenpng.net/ 2>/dev/null || true
echo

echo "=== Git ==="
git remote -v 2>/dev/null || true
git branch --show-current 2>/dev/null || true
git rev-parse HEAD 2>/dev/null || true
echo

echo "======================================================================"
echo " AUDIT COMPLETE - no services or files were changed"
echo "======================================================================"
