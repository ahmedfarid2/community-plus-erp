# Production deployment (cloud, multi-tenant)

Deploy the same Odoo stack to a Linux server with **wildcard HTTPS** and
**subdomain-per-company** multi-tenancy: `https://<company>.yourdomain.com`.

## What's different from local

| | Local (`docker-compose.yml`) | Production (`docker-compose.prod.yml`) |
|---|---|---|
| TLS | mkcert (`*.odoo.local`) | Let's Encrypt wildcard (DNS-01) |
| Multi-tenant | opt-in `dbfilter` | **on** (`dbfilter = ^%d$`) |
| DB manager (`list_db`) | on (selector) | **off** (security) |
| Exposed ports | 8069/8072 + 80/443 | only 80/443 |
| Renewal | n/a | certbot service, auto |
| Odoo workers | default | tuned (`workers = 4`) |

## Prerequisites

1. A Linux server (2+ vCPU, 4GB+ RAM) with Docker + Compose.
2. A domain, with **wildcard DNS**: `A  *.yourdomain.com -> SERVER_IP` and
   `A  yourdomain.com -> SERVER_IP`.
3. A Cloudflare API token (Zone:DNS:Edit) — wildcard certs need DNS-01.

## Steps

```bash
git clone <this repo> && cd odoo

# 1. Config + secrets
cp .env.production.example .env.production      # set DOMAIN, email, strong passwords
cp secrets/cloudflare.ini.example secrets/cloudflare.ini
chmod 600 secrets/cloudflare.ini                # paste your CF API token

# 2. Issue the wildcard certificate (once)
make prod-cert                                  # certbot DNS-01 -> letsencrypt volume

# 3. Deploy
make prod-deploy                                # renders prod config, starts the stack

# 4. Create a company (its own DB == its subdomain)
docker compose -f docker-compose.prod.yml run --rm web \
  odoo -d acme -i base,crm,sale_management,stock,purchase,account,hr,project,mrp,website \
  --stop-after-init --without-demo=all
```

Now `https://acme.yourdomain.com` serves **only** the `acme` company. Add more
companies by repeating step 4 with a new name → new subdomain.

## Operations

- **Logs / status:** `make prod-logs` · `docker compose -f docker-compose.prod.yml ps`
- **Backups:** the `scripts/backup.sh` approach works — point it at the prod compose,
  or run `pg_dump` against `odoo-prod-db`. Schedule nightly via cron.
- **Cert renewal:** automatic (the `certbot` service runs `certbot renew` every 12h;
  nginx reloads every 6h). No action needed.
- **Updates:** `docker compose -f docker-compose.prod.yml pull && make prod-deploy`,
  then run Odoo module updates per database: `... odoo -d <db> -u all --stop-after-init`.

## Security checklist

- [ ] `MASTER_PASSWORD` and `POSTGRES_PASSWORD` are long and unique (not the dev values).
- [ ] `list_db = False` (default in prod config) — DB manager not public.
- [ ] Firewall: only 80/443 open to the world; 8069/5432 not exposed (they aren't published).
- [ ] `secrets/cloudflare.ini` is `chmod 600` and gitignored.
- [ ] Off-site backups scheduled and test-restored.

## Other DNS providers

`docker-compose.prod.yml` uses `certbot/dns-cloudflare`. For Route 53, swap the image to
`certbot/dns-route53` and provide AWS creds; for others use the matching `certbot/dns-*`
image and credentials file, adjusting `scripts/prod/issue-cert.sh` flags accordingly.
