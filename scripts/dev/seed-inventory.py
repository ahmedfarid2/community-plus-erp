"""Seed clickable inventory-optimization demo data: products with controlled
stock + demand, then run the analysis to populate stock health, alerts and
reorder recommendations. Idempotent (skips if the demo products exist).
Run via: odoo shell -d <db> < scripts/dev/seed-inventory.py"""
from datetime import datetime, timedelta

H = env["inventory.stock.health"]
M = env["stock.move"]
P = env["product.product"]
Rule = env["inventory.optimization.rule"]
admin = env.ref("base.user_admin")
admin.write({"group_ids": [(4, env.ref(
    "advanced_inventory_optimization.group_inv_admin").id)]})

if not Rule.search([], limit=1):
    Rule.create({"name": "Default Optimization Rule"})

wh = env["stock.warehouse"].search([], limit=1)
SL = wh.lot_stock_id
cust = env.ref("stock.stock_location_customers")
sup = env.ref("stock.stock_location_suppliers")
vendor = (env["res.partner"].search([("name", "=", "Steel Supply Co")], limit=1)
          or env["res.partner"].search([("is_company", "=", True)], limit=1))


def product(name, cost):
    p = P.search([("name", "=", name)], limit=1)
    if not p:
        p = P.create({"name": name, "is_storable": True, "standard_price": cost,
                      "purchase_ok": True,
                      "seller_ids": [(0, 0, {"partner_id": vendor.id})]})
    return p


def set_stock(p, qty):
    env["stock.quant"]._update_available_quantity(p, SL, qty)


def demand(p, total_qty, over_days, spread_days):
    """Record `total_qty` outgoing over the period (one move, dated in past)."""
    m = M.create({"product_id": p.id, "product_uom_qty": total_qty,
                  "location_id": SL.id, "location_dest_id": cust.id,
                  "state": "done"})
    m.date = datetime.now() - timedelta(days=spread_days)


if H.search_count([("product_id.name", "like", "OPT ")]):
    print("inventory demo already seeded — skipping")
else:
    # Fast mover, understocked -> stockout risk + reorder recommendation
    fast = product("OPT Fast Mover", 12)
    set_stock(fast, 8)
    demand(fast, 90, 90, 45)            # ~1/day, coverage ~8 days

    # Steady, healthy
    healthy = product("OPT Steady", 20)
    set_stock(healthy, 60)
    demand(healthy, 90, 90, 45)         # ~1/day, coverage ~60 days

    # Overstocked, slow demand
    over = product("OPT Overstock", 8)
    set_stock(over, 500)
    demand(over, 90, 90, 45)            # ~1/day, coverage ~500 days

    # Dead stock: stock but no movement for ~300 days
    dead = product("OPT Dead Stock", 30)
    set_stock(dead, 40)
    mb = M.create({"product_id": dead.id, "product_uom_qty": 40,
                   "location_id": sup.id, "location_dest_id": SL.id,
                   "state": "done"})
    mb.date = datetime.now() - timedelta(days=300)

    env.invalidate_all()
    products = fast + healthy + over + dead
    H._run_analysis(products=products)
    print("ran analysis on %s demo products" % len(products))

env.cr.commit()
print("Health=%s Alerts=%s Recommendations=%s" % (
    H.search_count([("product_id.name", "like", "OPT ")]),
    env["inventory.alert"].search_count([("product_id.name", "like", "OPT ")]),
    env["inventory.reorder.recommendation"].search_count(
        [("product_id.name", "like", "OPT ")])))
