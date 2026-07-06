# Community Plus ERP — Odoo 19 Community Suite

A complete, **license-clean Odoo 19 Community** stack that delivers
Enterprise-grade capability without Enterprise: a Dockerized multi-company
platform plus **seven commercial product lines** — each an industry-agnostic,
reusable engine built from scratch, decoupled at the core (`base` + `mail`, plus
`product`/`stock` where needed) with optional integrations layered on top.

It is Odoo Community, audited open-source addons, and custom clean-room modules —
**not** unpaid Odoo Enterprise, and it must not be sold as official Enterprise
unless the client buys valid Enterprise licensing.

**License:** LGPL-3 · **Odoo:** 19.0 Community · **Stack:** Docker (odoo:19 +
postgres:16 + nginx) · **Tenancy:** one isolated database per company,
reachable at `https://<company>.odoo.local`.

---

## The product lines

Each is a standalone, sellable module family: a generic core + optional
integrations, Requester/User/Manager/Admin security profiles, demo data, an
app-store description page, and an idempotent seeder.

| Product | Core | Optional integrations |
|---------|------|-----------------------|
| **Payment Plans & Collections** | `payment_plan_core` | `payment_plan_account`, `payment_plan_reports` |
| **Smart Approval Workflow** | `smart_approval_workflow` | `_purchase`, `_account`, `_sale`, `_inventory`, `_hr`, `_payment_plan` (+ portal approve-link & escalation cron) |
| **Smart CPQ & Quotation Builder** | `smart_cpq_builder` | `smart_cpq_sale`, `smart_cpq_approval_workflow` |
| **Smart Subscription Manager** | `smart_subscription_manager` | `smart_subscription_account`, `smart_subscription_approval` |
| **Smart Field Service Suite** | `smart_field_service_suite` | `smart_fsm_account`, `smart_fsm_approval_workflow` |
| **Advanced Procurement Suite** | `advanced_procurement_suite` | `advanced_procurement_purchase`, `advanced_procurement_approval_workflow` |
| **Advanced Inventory Optimization** | `advanced_inventory_optimization` | `advanced_inventory_purchase`, `advanced_inventory_procurement`, `advanced_inventory_approval_workflow` |

Plus **Enterprise-parity `*_lite` apps** (Helpdesk, Field Service, Subscriptions
dashboards, Appraisals, Quality, Sign, Referrals, Documents, Knowledge, Marketing
Automation, an AI assistant, Phone, and more), a shared `community_plus_theme`,
and the `community_plus_sme_trading` meta-pack.

## What makes it composable

- **Decoupled cores.** Every product engine depends only on `base`+`mail` (plus
  `product`/`stock` when it genuinely reads them). Sale / account / purchase /
  approval coupling lives in *separate* optional modules — so a core is sellable
  on its own.

- **A cross-product approval mesh.** One generic `smart_approval_workflow` engine
  gates **12 document types across 6 products** — via a domain/amount rule and a
  single `create_for_record` call, with **zero changes** to any core:

  | Trigger | Product |
  |---------|---------|
  | PO / vendor bill > 5,000 | Purchase / Account |
  | Sales discount > 1,000 | Sales |
  | Payment-plan waiver > 500 | Payment Plans |
  | Expense > 300 | HR |
  | Outgoing delivery | Inventory (stock) |
  | CPQ margin < 15% | CPQ |
  | Subscription cancel, MRR ≥ 500 | Subscriptions |
  | Work order cost ≥ 500 | Field Service |
  | Procurement award ≥ 5,000 | Procurement |
  | Reorder cost ≥ 1,000 | Inventory Optimization |
  | Dead-stock disposal ≥ 500 | Inventory Optimization |

- **A procure-to-stock chain.** Inventory Optimization detects a reorder need →
  Procurement sources it via RFQ / vendor comparison / award → Purchase raises the
  PO. Three separate products composing into one pipeline.

## Design & compatibility

- **Odoo 19-native throughout:** `<list>` / `<chatter/>`, `t-name="card"` kanban,
  `res.groups.privilege`, `models.Constraint`, `group_ids` / `all_user_ids`, no
  `<group expand>` in search views, no `@string` xpath selectors, and safe formula
  evaluation via `odoo.tools.safe_eval` (never raw `eval`).
- **No Enterprise dependencies** — everything runs on Community.
- **Read-only where it matters** — the inventory engine reads `stock` data but
  never writes stock quantities or alters Odoo stock behavior.

---

## Architecture

- **One Odoo + one PostgreSQL, multi-database.** Each company is a separate Odoo
  database — separate data, logins, and installed apps.
- **nginx reverse proxy** terminates HTTPS and routes `https://<company>.odoo.local`
  to Odoo. Set `dbfilter = ^%d$` to make each subdomain serve only its own company
  (true multi-tenant); off by default (the database selector works everywhere).
- **Isolated stack per company** (optional): `make isolated name=acme` runs a
  separate Odoo + PostgreSQL on its own port/volumes — the bridge to per-client
  cloud hosting.

```
addons/                     custom modules (each with its own README + manifest)
  <product>_*/              the 7 product lines (core + integrations)
  *_lite/                   Enterprise-parity apps · community_plus_theme/
  oca/  odoomates/          vendored third-party (AGPL/LGPL upstream)
config/odoo.conf.template   base config, rendered on start (secrets from .env)
docker-compose.yml          nginx + postgres:16 + odoo:19
Makefile                    task runner — `make help`
scripts/                    lifecycle, onboarding, backup, dev seeders, pack-test
docs/                       positioning, deployment, feature matrix
```

Each module has its own `README.md` and `static/description/index.html` (its
app-store page) — start there for feature detail.

## Quick start

Prerequisites: **Docker Desktop** running, and **mkcert** for local HTTPS
(`brew install mkcert nss`).

```bash
git clone https://github.com/ahmedfarid2/community-plus-erp.git
cd community-plus-erp
cp .env.example .env            # then edit MASTER_PASSWORD / POSTGRES_PASSWORD
make https                      # one-time: trust local CA + issue *.odoo.local cert
make up                         # start (renders config, waits until reachable)
```

Add the local domains to `/etc/hosts` (once, sudo):

```bash
sudo sh -c 'echo "127.0.0.1 odoo.local acme.odoo.local globex.odoo.local" >> /etc/hosts'
```

Open **http://localhost:8069** (database manager; master password =
`MASTER_PASSWORD` from `.env`), create a company database, and install any product.

### Create a company

```bash
make client-init name=acme country=EG company="Acme Trading LLC"   # sellable pack
make company name=globex modules=base,crm,sale_management,stock    # custom app set
make company name=newco modules=all                                 # every Community app
```

- Subdomain: **https://acme.odoo.local** · Direct/admin: **http://localhost:8069**
- Login: `admin` / `admin` — **change it on first login**

### Demo data & seeders

Each product ships an idempotent seeder under `scripts/dev/`:

```bash
docker compose run --rm --no-deps -T web odoo shell -d acme --no-http < scripts/dev/seed-cpq.py
# seed-payment-plans.py · seed-subscriptions.py · seed-fsm.py · seed-procurement.py
# seed-inventory.py · seed-approval-workflows.py · seed-approval-requests.py
```

### Daily commands

```bash
make ps            # status              make logs           # tail Odoo logs
make backup db=acme# dump one company    make shell db=acme  # Odoo python shell
make down          # stop (keeps data)   make wipe           # DANGER: delete all data
```

`./scripts/dev/pack-test.sh` runs the fresh-DB install gate for the meta-pack.

## Path to the cloud

The same compose runs on a Linux VPS: keep the nginx `reverse_proxy`, swap mkcert
certs for Let's Encrypt (or Caddy), point a wildcard `*.yourdomain.com` at the
server, set strong passwords, and schedule `make backup`. `proxy_mode = True` is
already set. See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## License

**LGPL-3** — see [LICENSE](LICENSE). Every module declares `"license": "LGPL-3"`.
This repo contains no unlicensed Enterprise code.
