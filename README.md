# Odoo Community Plus ERP — multi-company stack

Run a legal **Odoo 19 Community Plus ERP** stack with Docker. The product is Odoo
Community, audited open-source addons, and custom clean-room modules. It is not unpaid
Odoo Enterprise, and it must not be sold as official Enterprise unless the client buys
valid Odoo Enterprise licensing.

Every company gets its **own isolated database** — separate data, separate logins, its own
installed apps — reachable at **`https://<company>.odoo.local`**. The first sellable pack is
for SME trading companies: CRM, Sales, Invoicing/Accounting, Inventory, Purchase, HR
basics, Project, Manufacturing basics, Website/eCommerce, POS, Expenses, and Loans Lite.

## Tooling — why it's built this way

- **Docker Compose** orchestrates everything (same as your other backends). There is no
  nx/pnpm here — those are JavaScript tools; Odoo is Python.
- **`make`** is the task runner / "manager" — `make up`, `make company name=acme`. Run
  `make help` to see all targets.
- **nginx reverse proxy + mkcert HTTPS + `*.odoo.local`** follows the project house style
  (`.docker/dev/nginx/default.conf` + `certs/`, local domain via `/etc/hosts`).

## Architecture

- **One Odoo + one PostgreSQL, multi-database.** Each company is a separate Odoo database.
- **nginx reverse proxy** terminates HTTPS and routes `https://<company>.odoo.local` to Odoo.
- **Subdomain → company database** (opt-in): set `dbfilter = ^%d$` in
  `config/odoo.conf.template` so each subdomain serves only its own company (no selector).
  Off by default — the database selector works everywhere until you turn it on.
- **Isolated stack per company** (optional): `make isolated name=acme` runs a completely
  separate Odoo + PostgreSQL on its own port/volumes — the bridge to per-client cloud hosting.

```
docker-compose.yml             reverse_proxy (nginx) + db (postgres) + web (odoo)
.docker/dev/nginx/default.conf nginx config (web + websocket upstreams, HTTPS)
.docker/dev/nginx/certs/       mkcert certs (gitignored)
config/odoo.conf.template      base config; rendered to config/odoo.conf on start
addons/                        your custom modules (mounted into the container)
Makefile                       task runner — `make help`
scripts/start.sh|stop.sh       lifecycle
scripts/new-company.sh         add a company (DB by default, or --isolated stack)
scripts/backup.sh|restore.sh   per-company backup / restore
scripts/dev/setup-https.sh     generate local HTTPS certs (mkcert)
.env                           versions, ports, passwords (gitignored)
```

## Prerequisites

- **Docker Desktop** (running): `docker compose version`
- **mkcert** for local HTTPS: `brew install mkcert nss`

## Quick start

```bash
cd /Users/farid/Documents/odoo
cp .env.example .env            # then edit MASTER_PASSWORD / POSTGRES_PASSWORD
make https                      # one-time: trust local CA + issue *.odoo.local cert
make up                         # start (renders config, waits until reachable)
```

Add the local domains to `/etc/hosts` (once, sudo):

```bash
sudo sh -c 'echo "127.0.0.1 odoo.local acme.odoo.local globex.odoo.local" >> /etc/hosts'
```

Open **http://localhost:8069** (admin / database manager) — master password =
`MASTER_PASSWORD` from `.env`.

### Create a sellable Community Plus client

```bash
make client-init name=acme country=EG company="Acme Trading LLC"
make client-health db=acme
make client-export db=acme
make client-upgrade db=acme
```

This installs `community_plus_sme_trading`, brands the main company, and checks the
database. Deep seeded smoke tests are still available with:

```bash
make seed db=acme
CLIENT_HEALTH_DEEP=1 make client-health db=acme
```

### Create a local/demo company

```bash
make company name=acme                       # Community Plus SME trading pack
make company name=globex modules=base,crm,sale_management,stock   # custom app set
make company name=newco modules=all          # EVERY Community app installed
```
Add every Community app to an existing company (POS, eCommerce, Events, Marketing,
Recruitment, Fleet, Maintenance, Surveys, eLearning, Time Off, Expenses...). It skips
Odoo's Enterprise-only upsells automatically:
```bash
make all-apps db=acme
```
- Subdomain: **https://acme.odoo.local**
- Direct/admin: **http://localhost:8069** → pick database `acme`
- Login: `admin` / `admin` — **change it on first login**

### Daily commands

```bash
make ps                 # status
make logs               # tail Odoo logs
make seed db=acme       # load demo data (customers, products, SO/PO, invoices,
                        #   CRM, stock on-hand, employees). reset=1 to re-create.
make backup db=acme     # dump one company (DB + filestore)
make shell db=acme      # Odoo python shell
make psql db=acme       # SQL console
make down               # stop (keeps data)
make wipe               # DANGER: delete ALL company data
```

### Turn on subdomain-per-company (true multi-tenant)

Uncomment `dbfilter = ^%d$` in `config/odoo.conf.template`, then `make restart`. Now
`https://acme.odoo.local` serves **only** the `acme` database (no selector). Verified:
each subdomain's database list returns just its own company.

## Accounting note (Community vs Enterprise)

Community includes **Invoicing/Accounting** foundations: chart of accounts, journals,
journal entries, taxes, invoices, payments, and bank reconciliation. Enterprise adds
proprietary polish and additional apps. This repo avoids unlicensed Enterprise code.

The disabled `account_financial_reports_lite` module is kept as reference work. For client
delivery, use maintained open-source reporting modules after a license/version audit, or
build clean custom reports. See [docs/FEATURE_MATRIX.md](docs/FEATURE_MATRIX.md).

## Path to the cloud

The same compose runs on a Linux VPS: keep the nginx `reverse_proxy`, swap mkcert certs for
Let's Encrypt (or Caddy), point a real domain's wildcard `*.yourdomain.com` at the server,
set strong passwords, and schedule `make backup`. `proxy_mode = True` is already set.

## Troubleshooting

- **Port 80/443 in use:** set `HTTP_PORT`/`HTTPS_PORT` in `.env` (e.g. 8080/8443), `make restart`.
- **Cert warning in browser:** re-run `make https`, restart the browser.
- **Subdomain not resolving:** confirm the `/etc/hosts` line (`make hosts` prints it).
- **Logs:** `make logs` · **Status:** `make ps`
