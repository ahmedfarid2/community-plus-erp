#!/usr/bin/env bash
# Give a company a real identity: name, country, and an auto-generated logo
# (square with the initial; colour derived deterministically from the name).
#
#   scripts/dev/brand-company.sh <db> "<Company Name>" [COUNTRY_CODE] [city] [email]
# Example:
#   scripts/dev/brand-company.sh acme "Acme Inc." US "San Francisco" info@acme.example.com
set -euo pipefail
cd "$(dirname "$0")/../.."

DB="${1:-}"; NAME="${2:-}"
[ -n "$DB" ] && [ -n "$NAME" ] || { echo 'Usage: brand-company.sh <db> "<Name>" [CC] [city] [email]'; exit 1; }
export BRAND_NAME="$NAME"
export BRAND_COUNTRY="${3:-US}"
export BRAND_CITY="${4:-}"
export BRAND_EMAIL="${5:-}"

ODOO_COMPOSE_FILE="${ODOO_COMPOSE_FILE:-docker-compose.yml}"
compose() {
  if [ -n "${ODOO_ENV_FILE:-}" ]; then
    docker compose -f "$ODOO_COMPOSE_FILE" --env-file "$ODOO_ENV_FILE" "$@"
  else
    docker compose -f "$ODOO_COMPOSE_FILE" "$@"
  fi
}

compose run --rm --no-deps -T \
  -e BRAND_NAME -e BRAND_COUNTRY -e BRAND_CITY -e BRAND_EMAIL \
  web odoo shell -d "$DB" --no-http <<'PY'
import base64, hashlib, io, os
from PIL import Image, ImageDraw, ImageFont

name = os.environ["BRAND_NAME"]
letter = (name.strip()[:1] or "C").upper()
# Deterministic brand colour from the name hash.
h = hashlib.md5(name.encode()).digest()
color = (60 + h[0] % 150, 60 + h[1] % 150, 60 + h[2] % 150)

company = env.ref("base.main_company")
vals = {"name": name}
cc = os.environ.get("BRAND_COUNTRY")
if cc:
    country = env["res.country"].search([("code", "=", cc)], limit=1)
    if country:
        vals["country_id"] = country.id
if os.environ.get("BRAND_CITY"):  vals["city"]  = os.environ["BRAND_CITY"]
if os.environ.get("BRAND_EMAIL"): vals["email"] = os.environ["BRAND_EMAIL"]

img = Image.new("RGB", (256, 256), color); d = ImageDraw.Draw(img)
font = None
for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
          "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"):
    try: font = ImageFont.truetype(p, 150); break
    except Exception: pass
if font is None: font = ImageFont.load_default()
try:
    b = d.textbbox((0, 0), letter, font=font); w = b[2]-b[0]; ht = b[3]-b[1]
    d.text(((256-w)/2-b[0], (256-ht)/2-b[1]), letter, fill=(255, 255, 255), font=font)
except Exception:
    d.text((90, 60), letter, fill=(255, 255, 255), font=font)
buf = io.BytesIO(); img.save(buf, "PNG")
vals["logo"] = base64.b64encode(buf.getvalue())

company.write(vals); env.cr.commit()
print("✓ branded:", company.name, "| country", company.country_id.name or "-")
PY
