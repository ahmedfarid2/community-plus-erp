# Odoo Community — multi-company local stack

Run **Odoo 19 Community** (free, open-source, unlimited users) on your Mac with Docker.
Every company gets its **own isolated database** — separate data, separate logins, its own
installed apps. All standard modules are available: CRM, Sales, Invoicing, Inventory,
Purchase, Accounting, HR, Project, Manufacturing, Website, and more.

## Architecture

- **Default — multi-database (recommended to start):** one Odoo container + one PostgreSQL
  container. Each company is a separate Odoo database. You pick the company's database at
  login. Lowest resource use, one command to add a company.
- **Optional — isolated stack per company:** `scripts/new-company.sh <name> --isolated`
  spins up a completely separate Odoo + PostgreSQL on its own port and volumes. Use this
  for hard isolation, or as the stepping stone to giving a client their own cloud server.

```
docker-compose.yml      Odoo + PostgreSQL (multi-database)
config/odoo.conf.template   base config; rendered to config/odoo.conf on start
addons/                 your custom modules (mounted into the container)
scripts/start.sh        render config + start + wait until reachable
scripts/stop.sh         stop (add --wipe to delete all data)
scripts/new-company.sh  add a company (DB by default, or --isolated stack)
scripts/backup.sh       dump one company (DB + filestore)
scripts/restore.sh      restore one company from a backup
.env                    versions, ports, passwords (gitignored)
```

## Prerequisites

- **Docker Desktop** for Mac (running). Check: `docker compose version`.

## Quick start

```bash
cd /Users/farid/Documents/odoo
cp .env.example .env        # then edit MASTER_PASSWORD / POSTGRES_PASSWORD
./scripts/start.sh          # pulls images, starts, waits until ready
```

Open **http://localhost:8069**. The database manager appears (master password =
`MASTER_PASSWORD` from `.env`).

### Create your first company

Two ways:

- **Web UI:** on the database-selector page click **Create database**, enter the master
  password, a database name (the company), an admin email + password, pick a country, and
  create. Then go to **Apps** and install what you need.
- **Command line (pre-installs the full suite):**
  ```bash
  ./scripts/new-company.sh acme
  # → database "acme", login: admin / admin  (change it immediately)
  ```
  Custom app list: `./scripts/new-company.sh acme base,crm,sale_management,stock,account`

### Add another company

```bash
./scripts/new-company.sh globex
```
`acme` and `globex` are fully separate — different users, products, and data. At login you
choose which company database to enter.

### Back up / move a company

```bash
./scripts/backup.sh acme
# → backups/acme-<timestamp>.dump  and  ...filestore.tar.gz
./scripts/restore.sh acme_copy backups/acme-<ts>.dump backups/acme-<ts>.filestore.tar.gz
```

### Stop / start

```bash
./scripts/stop.sh           # stop, keep all data
./scripts/start.sh          # start again
./scripts/stop.sh --wipe    # DANGER: delete every company's data
```

## Accounting note (Community vs Enterprise)

Community includes **Invoicing** (customer/vendor bills, payments). Full double-entry
**Accounting** reports (P&L, balance sheet, tax returns) are an Enterprise (paid) feature.
The community/OCA accounting modules cover most of this for free — install OCA
`account-financial-tools` / `account-financial-reporting` into `addons/` when you need the
full reports. Everything else (CRM, Sales, Inventory, Purchase, HR, Project, MRP, Website)
is fully featured in Community.

## Custom modules

Put a module folder in `addons/`, then in Odoo enable developer mode →
**Apps → Update Apps List** → install it. No infra change needed — `addons/` is already
mounted at `/mnt/extra-addons`.

## Path to the cloud (later)

The same `docker-compose.yml` runs on any Linux VPS (DigitalOcean, Hetzner, AWS…). For
production add a reverse proxy (Caddy or Nginx) terminating HTTPS in front of port 8069,
set strong passwords, set `proxy_mode = True` in `odoo.conf`, and schedule `backup.sh`.

## Troubleshooting

- **Logs:** `docker compose logs -f web`
- **Containers:** `docker compose ps`
- **Port 8069 in use:** change `ODOO_PORT` in `.env`, then `./scripts/start.sh`.
- **Forgot master password:** it's `MASTER_PASSWORD` in `.env`; re-run `./scripts/start.sh`
  to re-render `config/odoo.conf`.
