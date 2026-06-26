# Pre-delivery checklist (per client)

Run this before handing any client their Community Plus instance. Each step has a
command and a pass condition. **Stop and fix** if any step fails.

## 1. Codebase sanity

- [ ] On the intended release commit; working tree clean (`git status`).
- [ ] Third-party addons fetched: `./scripts/dev/fetch-thirdparty.sh`
- [ ] **Pack installs on a clean database:**
  ```bash
  make pack-test
  ```
  Pass: `PASS — 'community_plus_sme_trading' installs on a fresh database.`
  This is the gate — it pulls every dependency and the custom `*_lite` modules and
  fails on any error. Never deliver if this is red.

## 2. Provision the client company

- [ ] Create + brand + install the pack:
  ```bash
  make client-init name=<db> country=<CC> company="<Legal Name>"
  ```
- [ ] Wire accounting config (fiscal year + asset accounts):
  ```bash
  make setup-accounting db=<db>
  ```
- [ ] (Optional, for demos) load sample data:
  ```bash
  make seed db=<db>
  ```

## 3. Verify the running instance

- [ ] **Health check:**
  ```bash
  make client-health db=<db>
  CLIENT_HEALTH_DEEP=1 make client-health db=<db>   # deeper, with smoke data
  ```
- [ ] **Login + data smoke test:**
  ```bash
  make smoke db=<db>
  ```
  Pass: `PASS — '<db>' is healthy and populated.`

## 4. Security & data

- [ ] `.env` / `.env.production` secrets are strong and unique (not the dev defaults).
- [ ] Admin login password changed from the seed default.
- [ ] `list_db = False` in production config; only 80/443 exposed.
- [ ] First backup taken and **test-restored**:
  ```bash
  make backup db=<db>
  # then restore into a scratch db and open it
  ```

## 5. Scope & licensing

- [ ] Delivered features match [FEATURE_MATRIX.md](FEATURE_MATRIX.md).
- [ ] No unlicensed Enterprise code ships. Paid-only features (live bank sync, AI
      invoice OCR) are **not** promised unless the client buys Odoo Enterprise.
- [ ] Client told which modules are Native Community / vetted open-source / custom.

## 6. Production deploy (if hosting)

- [ ] Follow [DEPLOYMENT.md](DEPLOYMENT.md): wildcard cert, prod compose, nightly
      `make prod-backup-all`.
- [ ] `make pack-test` re-run after any module change before redeploying.

---

**Golden rule:** a green `make pack-test` + green `make smoke` are the two
non-negotiable gates. If either is red, the client does not get the build.
