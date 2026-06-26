#!/usr/bin/env bash
# Fetch third-party open-source accounting modules (Odoo Mates, LGPL-3) into addons/.
# Source: https://github.com/odoomates/odooapps (branch 19.0)
set -euo pipefail
cd "$(dirname "$0")/../.."
if [ -d addons/odoomates/.git ]; then
  echo "Updating addons/odoomates ..."; git -C addons/odoomates pull --ff-only
else
  echo "Cloning Odoo Mates accounting suite (19.0) ..."
  git clone --depth 1 -b 19.0 https://github.com/odoomates/odooapps.git addons/odoomates
fi
echo "✓ done. addons_path already includes /mnt/extra-addons/odoomates."
echo "  Install with: docker compose run --rm web odoo -d <db> -i om_account_accountant --stop-after-init"
