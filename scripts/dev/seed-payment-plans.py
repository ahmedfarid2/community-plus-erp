"""Seed demo data for the Payment Plans suite. Idempotent: re-running won't
duplicate. Run via: odoo shell -d <db> < scripts/dev/seed-payment-plans.py"""
from datetime import date
from dateutil.relativedelta import relativedelta

today = date.today()
Type = env["payment.plan.type"]
Tmpl = env["payment.plan.template"]
Plan = env["payment.plan"]
Partner = env["res.partner"]


def ensure(model, domain, vals):
    rec = model.search(domain, limit=1)
    if rec:
        return rec
    return model.create(vals)


# --- 0) Make the admin a Payment Plan Manager so menus/config are visible ---
mgr = env.ref("payment_plan_core.group_payment_plan_manager")
env.ref("base.user_admin").write({"group_ids": [(4, mgr.id)]})

# --- 1) Plan types -----------------------------------------------------------
t_install = ensure(Type, [("code", "=", "INSTALL")],
                   {"name": "Installments", "code": "INSTALL"})
t_mile = ensure(Type, [("code", "=", "MILESTONE")],
                {"name": "Milestone Payments", "code": "MILESTONE"})
t_ret = ensure(Type, [("code", "=", "RETAINER")],
               {"name": "Service Retainer", "code": "RETAINER"})
t_contract = ensure(Type, [("code", "=", "CONTRACT")],
                    {"name": "Contract Payments", "code": "CONTRACT"})

# --- 2) Templates ------------------------------------------------------------
tmpl_3m = ensure(Tmpl, [("name", "=", "3 Monthly Payments")],
                 {"name": "3 Monthly Payments", "number_of_payments": 3,
                  "frequency": "monthly", "equal_distribution": True,
                  "grace_period_days": 5})
tmpl_6m = ensure(Tmpl, [("name", "=", "6 Monthly Payments")],
                 {"name": "6 Monthly Payments", "number_of_payments": 6,
                  "frequency": "monthly", "equal_distribution": True,
                  "grace_period_days": 7})
tmpl_5050 = ensure(Tmpl, [("name", "=", "50 / 50 Payment")],
                   {"name": "50 / 50 Payment", "number_of_payments": 2,
                    "frequency": "monthly", "equal_distribution": False,
                    "first_payment_percent": 50.0, "grace_period_days": 0})
tmpl_qtr = ensure(Tmpl, [("name", "=", "Quarterly Contract")],
                  {"name": "Quarterly Contract", "number_of_payments": 4,
                   "frequency": "quarterly", "equal_distribution": True,
                   "grace_period_days": 10})
tmpl_ret = ensure(Tmpl, [("name", "=", "Monthly Retainer")],
                  {"name": "Monthly Retainer", "number_of_payments": 12,
                   "frequency": "monthly", "equal_distribution": True,
                   "grace_period_days": 3})

# --- 3) Customers across industries (showcases the generic product) ----------
def customer(name):
    return ensure(Partner, [("name", "=", name)],
                  {"name": name, "is_company": True, "customer_rank": 1})

c_academy = customer("Bright Future Academy")     # education
c_clinic = customer("Apex Dental Clinic")          # clinic
c_gym = customer("Peak Fitness Gym")               # gym
c_realty = customer("Skyline Properties")          # real estate
c_agency = customer("Nova Software Agency")        # agency / B2B

# --- 4) Plans (refresh: drop previously-seeded demo plans, then recreate) ----
demo_customers = c_academy + c_clinic + c_gym + c_realty + c_agency
Plan.search([("partner_id", "in", demo_customers.ids)]).unlink()
if True:
    def make_plan(partner, ptype, tmpl, total, months_ago, paid_map=None,
                  state="active"):
        """paid_map: {line_index: paid_amount}. months_ago backdates the start
        so some lines land in the past (overdue/paid)."""
        plan = Plan.create({
            "partner_id": partner.id,
            "plan_type_id": ptype.id,
            "template_id": tmpl.id,
            "total_amount": total,
            "start_date": today - relativedelta(months=months_ago),
        })
        plan.action_generate_lines()
        for idx, amt in (paid_map or {}).items():
            if idx < len(plan.line_ids):
                plan.line_ids[idx].paid_amount = amt
        if state == "active":
            plan.action_activate()
        elif state != "draft":
            plan.write({"state": state})
        return plan

    # Education: tuition, first month paid, 2nd unpaid & overdue (~30d), 3rd due.
    make_plan(c_academy, t_install, tmpl_3m, 3000.0, months_ago=2,
              paid_map={0: 1000.0})
    # Clinic: 50/50 treatment, deposit paid, balance unpaid & overdue (~30d).
    make_plan(c_clinic, t_mile, tmpl_5050, 1800.0, months_ago=2,
              paid_map={0: 900.0})
    # Gym: 6-month membership, 4 months in — 2 paid, then 2 overdue (~30/60d).
    make_plan(c_gym, t_ret, tmpl_6m, 720.0, months_ago=4,
              paid_map={0: 120.0, 1: 120.0})
    # Real estate: quarterly contract, 6 months in — Q1 paid, Q2 overdue (~90d).
    make_plan(c_realty, t_contract, tmpl_qtr, 40000.0, months_ago=6,
              paid_map={0: 10000.0})
    # Agency: healthy monthly retainer, current — first month paid, rest upcoming.
    make_plan(c_agency, t_ret, tmpl_ret, 12000.0, months_ago=1,
              paid_map={0: 1000.0})
    # A draft (not yet activated) plan to show the full lifecycle.
    make_plan(c_agency, t_mile, tmpl_3m, 4500.0, months_ago=0, state="draft")

    # --- 5) A couple of follow-ups on overdue customers ----------------------
    Followup = env["collection.followup"]
    gym_plan = Plan.search([("partner_id", "=", c_gym.id)], limit=1)
    overdue_line = gym_plan.line_ids.filtered(
        lambda l: l.status == "overdue")[:1]
    Followup.create({
        "partner_id": c_gym.id, "plan_id": gym_plan.id,
        "line_id": overdue_line.id if overdue_line else False,
        "followup_type": "call", "status": "planned",
        "next_action_date": today + relativedelta(days=3),
        "notes": "Called member — promised to settle the overdue month by Friday.",
    })
    realty_plan = Plan.search([("partner_id", "=", c_realty.id)], limit=1)
    Followup.create({
        "partner_id": c_realty.id, "plan_id": realty_plan.id,
        "followup_type": "email", "status": "done",
        "notes": "Sent Q2 reminder with the statement attached.",
    })

env.cr.commit()

# --- Summary -----------------------------------------------------------------
plans = Plan.search([])
lines = env["payment.plan.line"].search([])
overdue = lines.filtered(lambda l: l.status == "overdue")
print("SEED DONE: %s plans, %s lines (%s overdue), %s follow-ups" % (
    len(plans), len(lines), len(overdue),
    env["collection.followup"].search_count([])))
print("  total billed: %s | paid: %s | remaining: %s" % (
    sum(plans.mapped("total_amount")), sum(plans.mapped("paid_amount")),
    sum(plans.mapped("remaining_amount"))))
