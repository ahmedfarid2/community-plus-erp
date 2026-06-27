"""Seed clickable subscription demo data across industries + states.
Idempotent: skips if subscriptions already exist. Run via:
  odoo shell -d <db> < scripts/dev/seed-subscriptions.py"""
from datetime import date
from dateutil.relativedelta import relativedelta

P = env["subscription.plan"]
S = env["subscription.subscription"]
R = env["subscription.cancellation.reason"]
admin = env.ref("base.user_admin")
admin.write({
    "group_ids": [(4, env.ref(
        "smart_subscription_manager.group_subscription_admin").id)]})


def plan(code, name, ptype, period, price, **kw):
    p = P.search([("code", "=", code)], limit=1)
    if not p:
        p = P.create({"code": code, "name": name, "plan_type": ptype,
                      "billing_period": period, "price": price,
                      "state": "active", **kw})
    return p


saas = plan("SAAS-PRO", "SaaS Pro (Monthly)", "software", "monthly", 49,
            trial_days=14)
prem = plan("SAAS-PREM", "SaaS Premium (Monthly)", "software", "monthly", 99)
gym = plan("GYM-ANN", "Gym Membership (Annual)", "membership", "annual", 600,
           trial_days=7, minimum_contract_months=12)
maint = plan("MAINT-Q", "Maintenance (Quarterly)", "maintenance", "quarterly",
             300, grace_period_days=10)
svc = plan("SVC-RET", "Service Retainer (Monthly)", "service", "monthly", 1000)

for code, name in [("EXP", "Too Expensive"), ("SWITCH", "Switched Provider"),
                   ("NONEED", "No Longer Needed"), ("OTHER", "Other")]:
    if not R.search([("code", "=", code)], limit=1):
        R.create({"code": code, "name": name})


def customer(name):
    return env["res.partner"].search([("name", "=", name)], limit=1) \
        or env["res.partner"].search([("is_company", "=", True)], limit=1)


if S.search_count([]):
    print("subscriptions already exist — skipping")
else:
    academy = customer("Bright Future Academy")
    clinic = customer("Apex Dental Clinic")
    g_partner = customer("Peak Fitness Gym")
    realty = customer("Skyline Properties")
    agency = customer("Nova Software Agency")

    def make(partner, pl, months_ago, state="active", paid=0, overdue=False,
             auto=True, near_renewal=False):
        sub = S.create({
            "partner_id": partner.id, "plan_id": pl.id,
            "recurring_price": pl.price, "auto_renew": auto,
            "start_date": date.today() - relativedelta(months=months_ago)})
        if state in ("active", "paused"):
            sub.action_activate()
            sub.action_generate_billing()
            for ln in sub.billing_line_ids[:paid]:
                ln.action_mark_paid()
            if overdue and sub.billing_line_ids:
                due = sub.billing_line_ids.filtered(lambda l: l.state == "due")[:1]
                if due:
                    due.due_date = date.today() - relativedelta(days=8)
            if near_renewal:
                sub.renewal_date = date.today() + relativedelta(days=12)
            if state == "paused":
                sub.action_pause()
        return sub

    # SaaS — active, mostly paid, healthy
    make(agency, saas, 4, "active", paid=3)
    # Service — active, one overdue
    make(realty, svc, 2, "active", paid=1, overdue=True)
    # Maintenance — active, auto-renew OFF, renewal soon (at risk)
    make(clinic, maint, 3, "active", paid=2, auto=False, near_renewal=True)
    # Gym — trial
    g = S.create({"partner_id": g_partner.id, "plan_id": gym.id,
                  "recurring_price": gym.price, "start_date": date.today()})
    g.action_start_trial()
    # Maintenance — paused
    make(academy, maint, 5, "paused", paid=2)
    # SaaS — cancelled with reason
    c = make(agency, prem, 6, "active", paid=4)
    c._set_cancelled(R.search([("code", "=", "SWITCH")], limit=1), "Demo churn")

    # flip overdue lines + a metric snapshot
    S._cron_subscription_maintenance()
    env["subscription.metric.snapshot"].generate_snapshot()
    print("created %s subscriptions" % S.search_count([]))

env.cr.commit()
print("Plans=%s | Subscriptions=%s | by state=%s" % (
    P.search_count([]), S.search_count([]),
    {s: S.search_count([("state", "=", s)])
     for s in ("trial", "active", "paused", "cancelled")}))
