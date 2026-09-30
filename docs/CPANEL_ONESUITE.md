# OneSuite on cPanel

This profile runs Odoo 19 Community behind the existing cPanel Apache/AutoSSL
virtual host for `onesuite.nextgenpng.net`. Odoo and PostgreSQL never bind to
public interfaces.

## Runtime layout

- Public: `https://onesuite.nextgenpng.net`
- Odoo: `127.0.0.1:18069`
- Odoo websocket/gevent: `127.0.0.1:18072`
- PostgreSQL: internal container network only
- Database: `onesuite`
- Secrets: `.env.cpanel` (chmod 600, gitignored)

## Install

From the cPanel domain directory:

```bash
git init
git remote remove origin 2>/dev/null || true
git remote add origin https://github.com/austinkalisik/community-plus-erp.git
git fetch --depth=1 origin deploy/onesuite-cpanel-20260930
git checkout -B deploy/onesuite-cpanel-20260930 FETCH_HEAD
chmod +x scripts/cpanel/*.sh scripts/dev/fetch-thirdparty.sh
bash scripts/cpanel/audit.sh
bash scripts/cpanel/deploy.sh
```

If the audit/deployer reports that port 18069 already belongs to another Odoo
instance, do not stop or delete it. Inspect the existing stack first so its
database and filestore can be preserved.

After the backend is healthy, configure the cPanel Apache reverse proxy as root:

```bash
bash scripts/cpanel/apache-proxy-root.sh
```

Then open `https://onesuite.nextgenpng.net` and sign in as `admin`. The
generated password is stored in `.env.cpanel` under `ADMIN_PASSWORD`.

## OneSuite Hub

The `onesuite_hub` module provides a central launcher for external NextGen
systems. Administrators can add or edit launcher records without modifying code.
The initial launcher contains NexERP, NextGen B2B, TurProTrack, and the NextGen
corporate site.
