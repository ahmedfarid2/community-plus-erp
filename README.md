# Odoo Community — multi-company local stack

Run **Odoo 19 Community** (free, open-source, unlimited users) on your Mac with Docker.
Every company gets its **own isolated database** — separate data, separate logins, its own
installed apps — reachable at **`https://<company>.odoo.local`**. All standard modules are
available: CRM, Sales, Invoicing, Inventory, Purchase, Accounting, HR, Project,
Manufacturing, Website, and more.

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

### Create a company

```bash
make company name=acme                       # full standard suite
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

Community includes **Invoicing** (full double-entry: chart of accounts, journals, journal
entries, taxes, invoices, payments, bank reconciliation). The Enterprise **Accounting** app
adds polished financial reports. To get those for free, this repo ships a custom module
**`account_financial_reports_lite`** (in `addons/`) that adds **Trial Balance, Profit & Loss,
Balance Sheet, General Ledger and Aged Receivable/Payable** (interactive + PDF) under
*Accounting → Reporting → Financial Reports (Lite)*. It's installed by default for new
companies. (Don't click the **"Upgrade"** button on the Accounting app card — that's Odoo's
Enterprise upsell; these reports replace the paid ones for free.) Everything else (CRM, Sales,
Inventory, Purchase, HR, Project, MRP, Website) is fully featured in Community.

## Path to the cloud

The same compose runs on a Linux VPS: keep the nginx `reverse_proxy`, swap mkcert certs for
Let's Encrypt (or Caddy), point a real domain's wildcard `*.yourdomain.com` at the server,
set strong passwords, and schedule `make backup`. `proxy_mode = True` is already set.

## Troubleshooting

- **Port 80/443 in use:** set `HTTP_PORT`/`HTTPS_PORT` in `.env` (e.g. 8080/8443), `make restart`.
- **Cert warning in browser:** re-run `make https`, restart the browser.
- **Subdomain not resolving:** confirm the `/etc/hosts` line (`make hosts` prints it).
- **Logs:** `make logs` · **Status:** `make ps`
