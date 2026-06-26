# Idempotent demo-data seeder for one Odoo company database.
# Run via scripts/dev/seed.sh (pipes this file into `odoo shell`).
#
# Tunable via env vars (see seed.sh): SEED_CUSTOMERS, SEED_VENDORS, SEED_PRODUCTS,
# SEED_SALES, SEED_PURCHASES, SEED_LEADS. SEED_RESET=1 removes prior SEED-* records first.
#
# Records are tagged with a SEED- prefix (partner.ref, product.default_code,
# sale client_order_ref, purchase.partner_ref) so re-running tops up to target
# counts instead of duplicating. Degrades gracefully if an app isn't installed.

import os
fields = odoo.fields

def n(key, default):
    try: return int(os.environ.get(key, default))
    except ValueError: return int(default)

N_CUST  = n("SEED_CUSTOMERS", 12)
N_VEND  = n("SEED_VENDORS", 6)
N_PROD  = n("SEED_PRODUCTS", 15)
N_SALE  = n("SEED_SALES", 10)
N_PURCH = n("SEED_PURCHASES", 6)
N_LEAD  = n("SEED_LEADS", 8)
N_EMP   = n("SEED_EMPLOYEES", 8)
STOCK_QTY_BASE = n("SEED_STOCK", 100)        # on-hand qty for the first product, +10 each
RESET   = os.environ.get("SEED_RESET") == "1"

def has(model): return model in env

Partner = env["res.partner"]
Product = env["product.product"]

if RESET:
    print("… SEED_RESET=1 — removing previous SEED-* records")
    for mdl, dom in [
        ("sale.order",     [("client_order_ref", "like", "SEED-SO-%")]),
        ("purchase.order", [("partner_ref", "like", "SEED-PO-%")]),
        ("crm.lead",       [("name", "like", "SEED-LEAD-%")]),
        ("hr.employee",    [("name", "like", "Demo Employee %")]),
    ]:
        if has(mdl):
            try: env[mdl].search(dom).unlink()
            except Exception as e: print(f"   (skip {mdl}: {e})")
    Product.search([("default_code", "like", "SEED-P-%")]).unlink()
    Partner.search(["|", ("ref", "like", "SEED-C-%"), ("ref", "like", "SEED-V-%")]).unlink()

# ── Customers ───────────────────────────────────────────────────────────────
made = 0
for i in range(1, N_CUST + 1):
    ref = f"SEED-C-{i:03d}"
    if Partner.search([("ref", "=", ref)], limit=1):
        continue
    Partner.create({
        "name": f"Demo Customer {i:02d}",
        "ref": ref, "customer_rank": 1, "is_company": i % 3 == 0,
        "email": f"customer{i:02d}@example.com", "phone": f"+1000000{i:04d}",
    })
    made += 1
print(f"✓ customers: +{made} (target {N_CUST})")

# ── Vendors ─────────────────────────────────────────────────────────────────
made = 0
for i in range(1, N_VEND + 1):
    ref = f"SEED-V-{i:03d}"
    if Partner.search([("ref", "=", ref)], limit=1):
        continue
    Partner.create({
        "name": f"Demo Vendor {i:02d}", "ref": ref, "supplier_rank": 1,
        "is_company": True, "email": f"vendor{i:02d}@example.com",
    })
    made += 1
print(f"✓ vendors: +{made} (target {N_VEND})")

# ── Products ────────────────────────────────────────────────────────────────
made = 0
for i in range(1, N_PROD + 1):
    code = f"SEED-P-{i:03d}"
    if Product.search([("default_code", "=", code)], limit=1):
        continue
    vals = {
        "name": f"Demo Product {i:02d}", "default_code": code,
        "list_price": 50 + i * 10, "standard_price": 25 + i * 5, "type": "consu",
    }
    if "is_storable" in Product._fields:
        vals["is_storable"] = True            # track inventory (Odoo 17+ flag)
    Product.create(vals)
    made += 1
print(f"✓ products: +{made} (target {N_PROD})")

customers = Partner.search([("ref", "like", "SEED-C-%")])
vendors   = Partner.search([("ref", "like", "SEED-V-%")])
products  = Product.search([("default_code", "like", "SEED-P-%")])

# ── Sales orders (confirm half) ─────────────────────────────────────────────
if has("sale.order") and customers and products:
    SO = env["sale.order"]
    have = SO.search_count([("client_order_ref", "like", "SEED-SO-%")])
    made = 0
    for i in range(have + 1, N_SALE + 1):
        partner = customers[(i - 1) % len(customers)]
        lines = [(0, 0, {
            "product_id": products[(i + j) % len(products)].id,
            "product_uom_qty": 1 + (j % 5),
        }) for j in range(3)]
        so = SO.create({"partner_id": partner.id,
                        "client_order_ref": f"SEED-SO-{i:03d}",
                        "order_line": lines})
        if i % 2 == 0:
            try: so.action_confirm()
            except Exception as e: print(f"   (SO {i} confirm skipped: {e})")
        made += 1
    print(f"✓ sale orders: +{made} (target {N_SALE})")
else:
    print("– sale orders: skipped (sale app not installed)")

# ── Customer invoices for confirmed seeded SOs (if accounting present) ───────
if has("sale.order") and has("account.move"):
    posted = 0
    for so in env["sale.order"].search([("client_order_ref", "like", "SEED-SO-%"),
                                        ("state", "=", "sale"),
                                        ("invoice_status", "=", "to invoice")]):
        try:
            inv = so._create_invoices()
            inv.action_post()
            posted += len(inv)
        except Exception as e:
            print(f"   (invoice for {so.client_order_ref} skipped: {e})")
    print(f"✓ posted invoices: +{posted}")
else:
    print("– invoices: skipped (accounting not installed)")

# ── Purchase orders ─────────────────────────────────────────────────────────
if has("purchase.order") and vendors and products:
    from odoo.tests.common import Form        # drives onchanges → fills uom/price/dates
    PO = env["purchase.order"]
    have = PO.search_count([("partner_ref", "like", "SEED-PO-%")])
    made = 0
    for i in range(have + 1, N_PURCH + 1):
        vendor = vendors[(i - 1) % len(vendors)]
        try:
            po_form = Form(PO)
            po_form.partner_id = vendor
            for j in range(2):
                with po_form.order_line.new() as line:
                    line.product_id = products[(i + j) % len(products)]
                    line.product_qty = 2 + j
            po = po_form.save()
            po.partner_ref = f"SEED-PO-{i:03d}"
            made += 1
        except Exception as e:
            print(f"   (PO {i} skipped: {e})")
    print(f"✓ purchase orders: +{made} (target {N_PURCH})")
else:
    print("– purchase orders: skipped (purchase app not installed)")

# ── CRM opportunities ───────────────────────────────────────────────────────
if has("crm.lead") and customers:
    Lead = env["crm.lead"]
    have = Lead.search_count([("name", "like", "SEED-LEAD-%")])
    made = 0
    for i in range(have + 1, N_LEAD + 1):
        partner = customers[(i - 1) % len(customers)]
        Lead.create({
            "name": f"SEED-LEAD-{i:03d} — {partner.name}",
            "type": "opportunity", "partner_id": partner.id,
            "expected_revenue": 1000 + i * 250, "probability": (i * 7) % 100,
        })
        made += 1
    print(f"✓ crm opportunities: +{made} (target {N_LEAD})")
else:
    print("– crm: skipped (crm app not installed)")

# ── Inventory: set on-hand stock via inventory adjustment ───────────────────
if has("stock.quant") and products:
    wh = env["stock.warehouse"].search([], limit=1)
    loc = wh.lot_stock_id if wh else env.ref("stock.stock_location_stock",
                                              raise_if_not_found=False)
    Quant = env["stock.quant"]
    done = 0
    for idx, p in enumerate(products):
        # Only storable goods can hold stock.
        if "is_storable" in p._fields and not p.is_storable:
            continue
        if p.type != "consu":
            continue
        target = STOCK_QTY_BASE + idx * 10
        try:
            q = Quant.with_context(inventory_mode=True).create({
                "product_id": p.id, "location_id": loc.id,
                "inventory_quantity": target,        # absolute → idempotent
            })
            q.action_apply_inventory()
            done += 1
        except Exception as e:
            print(f"   (stock for {p.default_code} skipped: {e})")
    print(f"✓ stock on hand set on +{done} products")
else:
    print("– inventory: skipped (stock app not installed)")

# ── HR: departments + employees ─────────────────────────────────────────────
if has("hr.employee"):
    Emp = env["hr.employee"]
    roles = ["Sales Representative", "Accountant", "Warehouse Operator",
             "Project Manager", "HR Officer", "Buyer", "Support Agent"]
    Dept = env["hr.department"] if has("hr.department") else None
    dept_cache = {}
    if Dept is not None:
        for d in ["Sales", "Finance", "Warehouse", "Operations"]:
            rec = Dept.search([("name", "=", d)], limit=1) or Dept.create({"name": d})
            dept_cache[d] = rec
    dept_for = ["Sales", "Finance", "Warehouse", "Operations"]
    made = 0
    for i in range(1, N_EMP + 1):
        name = f"Demo Employee {i:02d}"
        if Emp.search([("name", "=", name)], limit=1):
            continue
        vals = {"name": name, "job_title": roles[i % len(roles)],
                "work_email": f"employee{i:02d}@example.com"}
        if dept_cache:
            vals["department_id"] = dept_cache[dept_for[i % len(dept_for)]].id
        Emp.create(vals)
        made += 1
    print(f"✓ employees: +{made} (target {N_EMP})"
          + (f", {len(dept_cache)} departments" if dept_cache else ""))
else:
    print("– hr: skipped (hr app not installed)")

# ── Community Plus apps: Approvals / Documents / Helpdesk / Subscriptions ────
import base64 as _b64
seed_customers = Partner.search([("ref", "like", "SEED-C-%")])

if has("business.approval.request"):
    Cat = env["business.approval.category"]
    cat = (Cat.search([("name", "=", "Purchase Approval")], limit=1)
           or Cat.create({"name": "Purchase Approval"}))
    Req = env["business.approval.request"]
    made = 0
    for i in range(1, 4):
        nm = f"SEED Approval {i:02d}"
        if Req.search([("name", "=", nm)], limit=1):
            continue
        Req.create({"name": nm, "category_id": cat.id})
        made += 1
    print(f"✓ approvals: +{made}")
else:
    print("– approvals: skipped (app not installed)")

if has("documents.lite.document"):
    Folder = env["documents.lite.folder"]
    folder = (Folder.search([("name", "=", "Contracts")], limit=1)
              or Folder.create({"name": "Contracts"}))
    Doc = env["documents.lite.document"]
    made = 0
    for i in range(1, 4):
        nm = f"SEED Doc {i:02d}.pdf"
        if Doc.search([("name", "=", nm)], limit=1):
            continue
        Doc.create({"name": nm, "folder_id": folder.id,
                    "document": _b64.b64encode(b"%PDF-1.4 seed")})
        made += 1
    print(f"✓ documents: +{made}")
else:
    print("– documents: skipped (app not installed)")

if has("helpdesk.lite.ticket"):
    Team = env["helpdesk.lite.team"]
    admin = env.ref("base.user_admin", raise_if_not_found=False)
    team = (Team.search([("name", "=", "Support")], limit=1)
            or Team.create({"name": "Support",
                            "user_id": admin.id if admin else False}))
    if admin and not team.user_id:
        team.user_id = admin.id  # so seeded tickets auto-assign + raise an activity
    Ticket = env["helpdesk.lite.ticket"]
    made = 0
    for i in range(1, 5):
        nm = f"SEED Ticket {i:02d}"
        if Ticket.search([("name", "=", nm)], limit=1):
            continue
        tv = {"name": nm}
        if "team_id" in Ticket._fields:
            tv["team_id"] = team.id
        if "partner_id" in Ticket._fields and seed_customers:
            tv["partner_id"] = seed_customers[i % len(seed_customers)].id
        Ticket.create(tv)
        made += 1
    print(f"✓ helpdesk tickets: +{made}")
else:
    print("– helpdesk: skipped (app not installed)")

if has("subscription.lite.contract") and seed_customers:
    Plan = env["subscription.lite.plan"]
    plan = (Plan.search([("name", "=", "Monthly")], limit=1)
            or Plan.create({"name": "Monthly", "interval_number": 1}))
    Sub = env["subscription.lite.contract"]
    made = 0
    for i in range(1, 4):
        nm = f"SEED-SUB-{i:03d}"
        if Sub.search([("name", "=", nm)], limit=1):
            continue
        Sub.create({"name": nm, "plan_id": plan.id,
                    "partner_id": seed_customers[i % len(seed_customers)].id})
        made += 1
    print(f"✓ subscriptions: +{made}")
else:
    print("– subscriptions: skipped (app not installed)")

env.cr.commit()
print("✓ seed committed.")
