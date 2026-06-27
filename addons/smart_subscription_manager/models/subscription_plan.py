from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError

# Months represented by one billing period (before applying the interval).
PERIOD_MONTHS = {
    "daily": 1.0 / 30.0,
    "weekly": 7.0 / 30.0,
    "monthly": 1.0,
    "quarterly": 3.0,
    "semi_annual": 6.0,
    "annual": 12.0,
    "custom": 1.0,
}


def period_months(period, interval):
    """Length of one billing cycle in months (used to normalize MRR/ARR)."""
    return PERIOD_MONTHS.get(period, 1.0) * max(interval or 1, 1)


def period_delta(period, interval):
    """relativedelta for one billing cycle."""
    interval = max(interval or 1, 1)
    return {
        "daily": relativedelta(days=interval),
        "weekly": relativedelta(weeks=interval),
        "monthly": relativedelta(months=interval),
        "quarterly": relativedelta(months=3 * interval),
        "semi_annual": relativedelta(months=6 * interval),
        "annual": relativedelta(years=interval),
        "custom": relativedelta(months=interval),
    }.get(period, relativedelta(months=interval))


class SubscriptionPlan(models.Model):
    _name = "subscription.plan"
    _description = "Subscription Plan"
    _inherit = ["mail.thread"]
    _order = "name"

    name = fields.Char(required=True, translate=True, tracking=True)
    code = fields.Char()
    active = fields.Boolean(default=True)
    state = fields.Selection(
        [("draft", "Draft"), ("active", "Active"), ("archived", "Archived")],
        default="draft", required=True, tracking=True)
    company_id = fields.Many2one(
        "res.company", default=lambda s: s.env.company)
    currency_id = fields.Many2one(
        "res.currency", required=True,
        default=lambda s: s.env.company.currency_id)
    product_id = fields.Many2one("product.product", string="Product")

    plan_type = fields.Selection(
        [("service", "Service"), ("membership", "Membership"),
         ("maintenance", "Maintenance"), ("software", "Software"),
         ("rental", "Rental"), ("custom", "Custom")],
        string="Plan Type", default="service", required=True)
    billing_period = fields.Selection(
        [("daily", "Daily"), ("weekly", "Weekly"), ("monthly", "Monthly"),
         ("quarterly", "Quarterly"), ("semi_annual", "Semi-annual"),
         ("annual", "Annual"), ("custom", "Custom")],
        string="Billing Period", default="monthly", required=True)
    billing_interval = fields.Integer(
        string="Billing Interval", default=1, required=True,
        help="Repeat every N periods (e.g. every 2 months).")
    price = fields.Monetary(currency_field="currency_id")
    setup_fee = fields.Monetary(currency_field="currency_id")
    trial_days = fields.Integer(string="Trial Days")
    minimum_contract_months = fields.Integer(string="Minimum Contract (months)")
    auto_renew = fields.Boolean(string="Auto Renew", default=True)
    grace_period_days = fields.Integer(string="Grace Period (days)", default=0)
    cancellation_policy = fields.Text()
    description = fields.Html(string="Customer Description")
    notes = fields.Text(string="Internal Notes")
    subscription_count = fields.Integer(compute="_compute_subscription_count")
    mrr_per_unit = fields.Monetary(
        currency_field="currency_id", compute="_compute_mrr_per_unit",
        string="MRR per Subscription",
        help="Monthly-normalized value of one subscription on this plan.")

    @api.depends("price", "billing_period", "billing_interval")
    def _compute_mrr_per_unit(self):
        for plan in self:
            months = period_months(plan.billing_period, plan.billing_interval)
            plan.mrr_per_unit = plan.price / months if months else 0.0

    def _compute_subscription_count(self):
        data = {}
        if self.ids:
            groups = self.env["subscription.subscription"]._read_group(
                [("plan_id", "in", self.ids)], ["plan_id"], ["__count"])
            data = {p.id: c for p, c in groups}
        for plan in self:
            plan.subscription_count = data.get(plan.id, 0)

    @api.constrains("price", "billing_interval")
    def _check_values(self):
        for plan in self:
            if plan.price < 0:
                raise ValidationError("Plan price cannot be negative.")
            if plan.billing_interval < 1:
                raise ValidationError("Billing interval must be at least 1.")

    def action_activate(self):
        self.write({"state": "active", "active": True})

    def action_archive_plan(self):
        self.write({"state": "archived", "active": False})

    def action_reset_to_draft(self):
        self.write({"state": "draft", "active": True})
