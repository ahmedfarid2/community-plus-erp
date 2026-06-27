"""Seed demo CPQ data across several industries. Idempotent: templates are
keyed by name and skipped if present. Run via:
  odoo shell -d <db> < scripts/dev/seed-cpq.py"""
T = env["cpq.template"]
G = env["cpq.option.group"]
O = env["cpq.option"]
PR = env["cpq.pricing.rule"]
CR = env["cpq.compatibility.rule"]
C = env["cpq.configuration"]

# Admin can configure CPQ.
admin = env.ref("base.user_admin")
admin.write({"group_ids": [(4, env.ref("smart_cpq_builder.group_cpq_admin").id)]})


def group(tmpl, name, sel="single", required=False, mx=0, seq=10):
    return G.create({
        "template_id": tmpl.id, "name": name, "code": name[:4].upper(),
        "selection_type": sel, "is_required": required,
        "max_selection": mx, "sequence": seq})


def option(grp, name, code, ptype="fixed", price=0.0, pct=0.0, cost=0.0,
           formula=False):
    return O.create({
        "group_id": grp.id, "name": name, "code": code, "price_type": ptype,
        "fixed_price": price, "percentage_value": pct, "cost": cost,
        "formula_expression": formula})


created = []


def ensure_template(name, base_price, builder):
    if T.search([("name", "=", name)], limit=1):
        print("  %-26s -> exists" % name)
        return None
    tmpl = T.create({"name": name, "code": name[:6].upper(),
                     "state": "active", "base_price": base_price})
    builder(tmpl)
    created.append(tmpl)
    print("  %-26s -> created" % name)
    return tmpl


# ---------------------------------------------------------- Aluminum Window
def build_window(t):
    mat = group(t, "Material", "single", True, seq=10)
    std = option(mat, "Standard Aluminum", "STD", "none", cost=60)
    prem = option(mat, "Premium Aluminum", "PREMIUM", "percentage", pct=15, cost=110)
    glz = group(t, "Glazing", "single", True, seq=20)
    option(glz, "Single Glazing", "SGL", "none", cost=20)
    option(glz, "Double Glazing", "DBL", "fixed", price=50, cost=35)
    acc = group(t, "Accessories", "multiple", mx=3, seq=30)
    handles = option(acc, "Premium Handles", "HANDLES", "fixed", price=25, cost=12)
    option(acc, "Mosquito Net", "NET", "fixed", price=15, cost=7)
    ins = group(t, "Installation", "single", seq=40)
    option(ins, "Professional Installation", "PRO", "fixed", price=60, cost=40)
    PR.create({"template_id": t.id, "name": "Bulk discount (qty > 10)",
               "sequence": 10, "condition_type": "quantity_based",
               "condition_expression": "quantity > 10",
               "price_action": "discount_percentage", "percentage": 5})
    CR.create({"template_id": t.id, "name": "Premium handles need premium aluminum",
               "rule_type": "requires", "source_option_id": handles.id,
               "target_option_id": prem.id, "severity": "blocking"})


# ---------------------------------------------------------- Custom Kitchen
def build_kitchen(t):
    cab = group(t, "Cabinet Material", "single", True, seq=10)
    option(cab, "MDF", "MDF", "none", cost=800)
    option(cab, "Solid Wood", "WOOD", "fixed", price=1500, cost=1900)
    top = group(t, "Countertop", "single", True, seq=20)
    option(top, "Laminate", "LAM", "none", cost=200)
    option(top, "Granite", "GRN", "fixed", price=900, cost=600)
    option(top, "Quartz", "QTZ", "fixed", price=1400, cost=1000)
    app = group(t, "Appliances", "multiple", seq=30)
    option(app, "Range Hood", "HOOD", "fixed", price=300, cost=180)
    option(app, "Sink", "SINK", "fixed", price=150, cost=90)
    # large-kitchen surcharge: +10% of total when area (W×H) over 15 m²
    PR.create({"template_id": t.id, "name": "Large kitchen surcharge (area > 15)",
               "sequence": 10, "condition_type": "formula_based",
               "condition_expression": "area > 15",
               "price_action": "add_percentage", "percentage": 10})


# ---------------------------------------------------------- Solar Package
def build_solar(t):
    cap = group(t, "Capacity", "single", True, seq=10)
    c3 = option(cap, "3 kW", "KW3", "none", cost=2500)
    option(cap, "5 kW", "KW5", "fixed", price=2500, cost=4500)
    kw10 = option(cap, "10 kW", "KW10", "fixed", price=7000, cost=9000)
    bat = group(t, "Battery", "single", seq=20)
    option(bat, "No Battery", "B0", "none")
    option(bat, "5 kWh", "B5", "fixed", price=1800, cost=1200)
    b10 = option(bat, "10 kWh", "B10", "fixed", price=3200, cost=2200)
    mnt = group(t, "Mounting", "single", True, seq=30)
    option(mnt, "Roof Mount", "ROOF", "none", cost=300)
    option(mnt, "Ground Mount", "GROUND", "fixed", price=800, cost=600)
    PR.create({"template_id": t.id, "name": "Installation fee (8%)",
               "sequence": 10, "condition_type": "always",
               "price_action": "add_percentage", "percentage": 8})
    CR.create({"template_id": t.id, "name": "10 kW recommends 10 kWh battery",
               "rule_type": "requires", "source_option_id": kw10.id,
               "target_option_id": b10.id, "severity": "warning",
               "message": "A 10 kW system is best paired with a 10 kWh battery."})


# ---------------------------------------------------------- Service Retainer
def build_service(t):
    tier = group(t, "Service Tier", "single", True, seq=10)
    option(tier, "Basic", "BASIC", "none", cost=400)
    option(tier, "Pro", "PRO", "fixed", price=1500, cost=900)
    option(tier, "Enterprise", "ENT", "fixed", price=4000, cost=2400)
    addon = group(t, "Add-ons", "multiple", seq=20)
    option(addon, "SEO", "SEO", "fixed", price=500, cost=250)
    option(addon, "Ads Management", "ADS", "fixed", price=800, cost=400)
    option(addon, "Content", "CONTENT", "fixed", price=600, cost=300)
    sup = group(t, "Support", "single", True, seq=30)
    option(sup, "Business Hours", "BH", "none", cost=100)
    option(sup, "24/7 Support", "247", "fixed", price=1200, cost=700)


ensure_template("Aluminum Window", 200.0, build_window)
ensure_template("Custom Kitchen", 3000.0, build_kitchen)
ensure_template("Solar System Package", 5000.0, build_solar)
ensure_template("Service Retainer Package", 1000.0, build_service)

# --- A few sample configurations (only if none seeded yet) ----------------
partner = env["res.partner"].search([("is_company", "=", True)], limit=1) \
    or env["res.partner"].search([], limit=1)


def opt_ref(tmpl_name, code):
    t = T.search([("name", "=", tmpl_name)], limit=1)
    return O.search([("template_id", "=", t.id), ("code", "=", code)], limit=1)


if created and not C.search([("template_id", "in",
                              T.search([]).ids)], limit=1):
    win = T.search([("name", "=", "Aluminum Window")], limit=1)
    cfg = C.create({
        "template_id": win.id, "partner_id": partner.id, "quantity": 4,
        "selected_option_ids": [(6, 0, [
            opt_ref("Aluminum Window", "PREMIUM").id,
            opt_ref("Aluminum Window", "DBL").id,
            opt_ref("Aluminum Window", "HANDLES").id,
            opt_ref("Aluminum Window", "PRO").id])]})
    cfg.action_validate()
    kit = T.search([("name", "=", "Custom Kitchen")], limit=1)
    C.create({
        "template_id": kit.id, "partner_id": partner.id, "quantity": 1,
        "selected_option_ids": [(6, 0, [
            opt_ref("Custom Kitchen", "WOOD").id,
            opt_ref("Custom Kitchen", "QTZ").id,
            opt_ref("Custom Kitchen", "HOOD").id])]})
    sol = T.search([("name", "=", "Solar System Package")], limit=1)
    C.create({
        "template_id": sol.id, "partner_id": partner.id, "quantity": 1,
        "selected_option_ids": [(6, 0, [
            opt_ref("Solar System Package", "KW5").id,
            opt_ref("Solar System Package", "B5").id,
            opt_ref("Solar System Package", "ROOF").id])]})
    print("  sample configurations -> created")

env.cr.commit()
print("Templates: %s | Configurations: %s" % (
    T.search_count([]), C.search_count([])))
