from odoo import fields, models


class SubscriptionChange(models.Model):
    _name = "subscription.change"
    _description = "Subscription Plan Change"
    _order = "effective_date desc, id desc"

    subscription_id = fields.Many2one(
        "subscription.subscription", string="Subscription", required=True,
        ondelete="cascade", index=True)
    currency_id = fields.Many2one(related="subscription_id.currency_id")
    change_type = fields.Selection(
        [("upgrade", "Upgrade"), ("downgrade", "Downgrade"),
         ("plan_change", "Plan Change"), ("price_change", "Price Change")],
        string="Change Type", required=True)
    old_plan_id = fields.Many2one("subscription.plan", string="Old Plan")
    new_plan_id = fields.Many2one("subscription.plan", string="New Plan")
    old_price = fields.Monetary(currency_field="currency_id")
    new_price = fields.Monetary(currency_field="currency_id")
    effective_date = fields.Date(default=fields.Date.context_today)
    proration_policy = fields.Selection(
        [("none", "None"), ("immediate", "Immediate"),
         ("next_cycle", "Next Cycle")],
        string="Proration", default="none", required=True)
    proration_amount = fields.Monetary(currency_field="currency_id")
    state = fields.Selection(
        [("draft", "Draft"), ("applied", "Applied"), ("cancelled", "Cancelled")],
        default="applied", required=True)
    reason = fields.Char()
    notes = fields.Text()
