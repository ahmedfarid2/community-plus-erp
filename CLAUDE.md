# Community Plus ERP

Dockerized multi-company Odoo 19 Community deployment: custom addons (seven
commercial product lines plus Enterprise-parity "lite" apps), nginx wildcard
TLS, Let's Encrypt, and vendored OCA add-ons. LGPL-3.0, public repo — no
secrets or client data belong here.

## Stack
- Odoo 19.0 Community, Python, PostgreSQL 16, nginx reverse proxy, Docker Compose
- Local HTTPS via mkcert; production wildcard HTTPS via certbot DNS-01 (Cloudflare)
- `make` is the task runner (`make help` lists targets)

## Structure
- `addons/` — custom modules: 7 product-line families (`payment_plan_*`,
  `smart_approval_*`, `smart_cpq_*`, `smart_subscription_*`, `smart_fsm_*`,
  `advanced_procurement_*`, `advanced_inventory_*`), `*_lite` apps,
  `community_plus_theme`, `community_plus_sme_trading` meta-pack, plus
  vendored `oca/` and `odoomates/` (gitignored, fetched by
  `scripts/dev/fetch-thirdparty.sh`)
- `config/` — `odoo.conf.template` / `odoo.prod.conf.template`, rendered by
  `scripts/start.sh` / `scripts/prod/deploy.sh`
- `docker/`, `.docker/` — Odoo `Dockerfile`; nginx configs (dev mkcert, prod template)
- `scripts/` — lifecycle (`start.sh`, `stop.sh`, `backup.sh`, `restore.sh`),
  client provisioning (`client-init.sh`, `onboard-client.sh`, `new-company.sh`,
  `client-upgrade.sh`, `client-export.sh`), `scripts/dev/` (seeders,
  `pack-test.sh`, `smoke-test.sh`), `scripts/prod/` (`issue-cert.sh`,
  `deploy.sh`, `backup-all.sh`)
- `secrets/` — `cloudflare.ini` (gitignored; only `.example` is committed)
- `docs/` — `DEPLOYMENT.md`, `TESTING.md`, `FEATURE_MATRIX.md`, `POSITIONING.md`

## Conventions
- Odoo 19-native APIs only: `<list>`/`<chatter/>`, `t-name="card"` kanban,
  `res.groups.privilege`, `models.Constraint`, `group_ids`/`all_user_ids`; no
  `<group expand>` in search views, no `@string` xpath selectors, safe formula
  eval via `odoo.tools.safe_eval` — never raw `eval`.
- Each product core depends only on `base`+`mail` (+ `product`/`stock` where
  genuinely needed); sale/account/purchase/approval coupling lives in
  separate optional integration modules, not the core.
- Each addon ships its own `README.md`, `static/description/index.html`
  (app-store page), and a manifest declaring `"license": "LGPL-3"`.
- No Enterprise dependencies anywhere — Community-only.

## Sensitive areas (critical-reviewer before COMPLETE)
- `docker-compose.prod.yml`, `.docker/production/**`, `scripts/prod/**` — production TLS/nginx/deploy and wildcard cert issuance
- `scripts/onboard-client.sh`, `scripts/client-init.sh`, `scripts/new-company.sh`, `scripts/client-upgrade.sh`, `scripts/client-export.sh` — client DB provisioning/lifecycle
- `config/odoo.prod.conf.template`, `config/odoo.conf.template` — rendered config, incl. `dbfilter`/`list_db` security settings
- `secrets/`, `.env.example`, `.env.production.example` — credential templates (never commit real values)
- `addons/*/security/**` — Odoo ACLs and record rules across all modules

## Validation
- `make pack-test` (`scripts/dev/pack-test.sh`) — fresh-DB install test for the `community_plus_sme_trading` meta-pack; fails on install errors or modules not reaching `installed`
- `make smoke db=<db>` (`scripts/dev/smoke-test.sh`) — logs in via API, checks core data is present
- `make client-health db=<db>` (`scripts/client-health.sh`) — health check for a client database
- Manual: `docs/TESTING.md` end-to-end business-cycle walkthrough (CRM → Sales → Invoicing → Inventory → Purchase)
- No automated Python unit-test suite or lint config exists in this repo (unverified beyond this)

## Engineering orchestration

@.claude/orchestration/POLICY.md
