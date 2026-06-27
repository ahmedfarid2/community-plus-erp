"""Seed clickable procurement demo data. Idempotent: skips if requests exist.
Run via: odoo shell -d <db> < scripts/dev/seed-procurement.py"""
from datetime import date, timedelta

CR = env["procurement.evaluation.criteria"]; CAT = env["procurement.vendor.category"]
VP = env["procurement.vendor.profile"]; REQ = env["procurement.request"]
RFQ = env["procurement.rfq.event"]; CON = env["procurement.vendor.contract"]
PR = env["procurement.performance.review"]
admin = env.ref("base.user_admin")
admin.write({"group_ids": [(4, env.ref(
    "advanced_procurement_suite.group_proc_admin").id)]})

for name, code, w in [("Price", "price", 40), ("Delivery Time", "delivery", 20),
                      ("Quality", "quality", 25), ("Vendor Risk", "risk", 15)]:
    if not CR.search([("code", "=", code)], limit=1):
        CR.create({"name": name, "code": code, "weight_percent": w})
raw = CAT.search([("code", "=", "RAW")], limit=1) or CAT.create(
    {"name": "Raw Materials", "code": "RAW"})
itc = CAT.search([("code", "=", "IT")], limit=1) or CAT.create(
    {"name": "IT Equipment", "code": "IT"})


def vendor(name):
    p = env["res.partner"].search([("name", "=", name)], limit=1)
    if not p:
        p = env["res.partner"].create({"name": name, "is_company": True,
                                       "supplier_rank": 1})
    return p


def profile(partner, risk, preferred=False, cats=None):
    prof = VP.search([("partner_id", "=", partner.id)], limit=1)
    if not prof:
        prof = VP.create({"partner_id": partner.id, "risk_level": risk,
                          "preferred_vendor": preferred,
                          "vendor_category_ids": [(6, 0, [c.id for c in (cats or [])])]})
    return prof


v_steel = vendor("Steel Supply Co"); profile(v_steel, "low", True, [raw])
v_tech = vendor("TechParts Ltd"); profile(v_tech, "medium", False, [itc])
v_build = vendor("BuildMart"); profile(v_build, "high")

if REQ.search_count([]):
    print("procurement data already exists — skipping")
else:
    prod = env["product.product"].search([], limit=1)

    # 1) A submitted/under-review request
    r1 = REQ.create({"request_type": "product", "priority": "high",
                     "justification": "Q3 production restock"})
    env["procurement.request.line"].create({
        "request_id": r1.id, "product_id": prod.id, "description": "Steel sheets 2mm",
        "quantity": 100, "estimated_unit_price": 25})
    r1.action_submit(); r1.action_review()

    # 2) A full sourced request: RFQ -> quotes -> award -> approved
    r2 = REQ.create({"request_type": "product", "priority": "medium",
                     "justification": "IT hardware refresh"})
    env["procurement.request.line"].create({
        "request_id": r2.id, "product_id": prod.id, "description": "Laptops",
        "quantity": 10, "estimated_unit_price": 900})
    r2.action_submit(); r2.action_review()
    rfq = RFQ.browse(r2.action_create_rfq()["res_id"])
    rfq.invited_vendor_ids = [(6, 0, [v_tech.id, v_build.id, v_steel.id])]
    rfq.action_open(); rfq.action_invite_vendors()
    prices = {v_tech.id: 850, v_build.id: 820, v_steel.id: 880}
    deliv = {v_tech.id: 7, v_build.id: 14, v_steel.id: 5}
    for q in rfq.vendor_quote_ids:
        q.delivery_date = date.today() + timedelta(days=deliv.get(q.vendor_id.id, 10))
        q.quote_line_ids.write({"unit_price": prices.get(q.vendor_id.id, 900),
                                "product_id": prod.id})
        q.action_submit()
    rfq.action_close(); rfq.action_start_evaluation()
    aw = env["procurement.award"].browse(rfq.action_create_award()["res_id"])
    aw.action_request_approval(); aw.action_approve()

    # 3) An open RFQ (in progress) for clicking through
    r3 = REQ.create({"request_type": "service", "priority": "low",
                     "justification": "Maintenance contract sourcing"})
    env["procurement.request.line"].create({
        "request_id": r3.id, "description": "Annual AC maintenance", "quantity": 1,
        "estimated_unit_price": 5000})
    r3.action_submit(); r3.action_review()
    rfq2 = RFQ.browse(r3.action_create_rfq()["res_id"])
    rfq2.invited_vendor_ids = [(6, 0, [v_steel.id, v_build.id])]
    rfq2.action_open(); rfq2.action_invite_vendors()

    # 4) Vendor contracts (one expiring soon)
    CON.create({"vendor_id": v_steel.id, "contract_type": "Supply Agreement",
                "state": "active", "contract_value": 50000,
                "start_date": date.today() - timedelta(days=340),
                "end_date": date.today() + timedelta(days=20)})
    CON.create({"vendor_id": v_tech.id, "contract_type": "Service SLA",
                "state": "active", "contract_value": 12000,
                "start_date": date.today() - timedelta(days=60),
                "end_date": date.today() + timedelta(days=300)})

    # 5) Performance reviews feeding profile scores
    PR.create({"vendor_id": v_steel.id, "quality_rating": 92, "delivery_rating": 95,
               "price_rating": 85, "service_rating": 90, "compliance_rating": 95,
               "delivery_delay_days": -1})
    PR.create({"vendor_id": v_build.id, "quality_rating": 70, "delivery_rating": 60,
               "price_rating": 88, "service_rating": 65, "compliance_rating": 70,
               "delivery_delay_days": 4})

    # flip contract states
    CON._cron_contract_reminders()
    print("seeded requests/RFQs/awards/contracts/reviews")

env.cr.commit()
print("Requests=%s RFQs=%s Awards=%s Vendors=%s Contracts=%s (expiring=%s)" % (
    REQ.search_count([]), RFQ.search_count([]),
    env["procurement.award"].search_count([]), VP.search_count([]),
    CON.search_count([]), CON.search_count([("state", "=", "expiring_soon")])))
