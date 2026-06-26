# Local test workflow

How to log in and verify a company end-to-end on your Mac.

## 0. Bring it up + load demo data

```bash
make up                 # start Odoo + db + nginx
make company name=acme  # create the company (skip if it already exists)
make seed db=acme       # load demo data (customers, products, sales, stock, HR...)
```

## 1. Log in (the "account")

Each company is its own database with its own users. The CLI-created admin account is:

| Field | Value |
|---|---|
| URL | **http://localhost:8069** |
| Database | `acme` (pick it in the selector) |
| Login | `admin` |
| Password | `admin` — **change on first login** |
| Master password (DB manager) | `MASTER_PASSWORD` in `.env` |

> Over HTTPS subdomains (`https://acme.odoo.local`) instead: run `make https` once, then
> add the host — `make hosts` prints the `/etc/hosts` line (needs sudo). Direct
> `localhost:8069` stays available for the database manager / admin.

Add more login accounts: **Settings → Users & Companies → Users → New** (set a login +
password, assign app access). That's how you "link" additional staff accounts to a company.

## 2. Automated smoke test (30 seconds)

Proves login works and the core data is present, without clicking:

```bash
make smoke db=acme      # logs in via API and checks customers/sales/invoices/...
make smoke db=globex
```
Expected: `PASS — '<db>' is healthy and populated.`

## 3. Manual end-to-end business cycle

Log in to `acme`, then walk the full lead-to-cash + supply chain:

1. **CRM** → *Sales → CRM → My Pipeline*: you'll see seeded opportunities. Drag one across
   stages; open one and click **New Quotation** to convert it.
2. **Sales** → *Sales → Orders → Quotations*: open a seeded quotation, **Confirm** it
   (becomes a Sales Order), then **Create Invoice → Regular invoice → Confirm**.
3. **Invoicing/Accounting** → *Accounting → Customers → Invoices*: open the posted invoice,
   **Register Payment** → Validate. The invoice shows **Paid**.
4. **Inventory** → *Inventory → Products*: open a seeded product → **On Hand** shows stock
   (acme has ~2,550 units across products). From a confirmed SO with a storable product,
   process the **Delivery** to see stock decrease.
5. **Purchase** → *Purchase → Orders*: open a seeded PO, **Confirm Order**, then **Receive
   Products** to add stock.
6. **Employees** → *Employees*: seeded staff across departments (Sales, Finance, Warehouse,
   Operations).

## 4. Reset / re-seed between tests

```bash
make seed db=acme reset=1   # remove SEED-* records and recreate a clean dataset
```

## Troubleshooting

- **"Database not found" on login / empty database selector** → the running Odoo has a
  stale config (e.g. after toggling `dbfilter`). Fix: `make restart`.
- **Can't reach https://acme.odoo.local** → `make https` not run, or missing `/etc/hosts`
  entry (`make hosts`). `localhost:8069` always works regardless.
- **Logs:** `make logs` · **Status:** `make ps`
