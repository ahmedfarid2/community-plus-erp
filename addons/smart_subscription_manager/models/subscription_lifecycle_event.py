from odoo import fields, models


class SubscriptionLifecycleEvent(models.Model):
    _name = "subscription.lifecycle.event"
    _description = "Subscription Lifecycle Event"
    _order = "event_date desc, id desc"

    subscription_id = fields.Many2one(
        "subscription.subscription", string="Subscription", required=True,
        ondelete="cascade", index=True)
    partner_id = fields.Many2one(
        related="subscription_id.partner_id", store=True, string="Customer")
    currency_id = fields.Many2one(related="subscription_id.currency_id")
    event_type = fields.Selection(
        [("created", "Created"), ("activated", "Activated"),
         ("trial_started", "Trial Started"), ("trial_ended", "Trial Ended"),
         ("renewed", "Renewed"), ("upgraded", "Upgraded"),
         ("downgraded", "Downgraded"), ("paused", "Paused"),
         ("resumed", "Resumed"), ("cancelled", "Cancelled"),
         ("expired", "Expired"), ("price_changed", "Price Changed"),
         ("billing_generated", "Billing Generated"),
         ("invoice_created", "Invoice Created"), ("note", "Note")],
        string="Event", required=True)
    event_date = fields.Datetime(default=fields.Datetime.now)
    user_id = fields.Many2one("res.users", string="User")
    old_plan_id = fields.Many2one("subscription.plan", string="Old Plan")
    new_plan_id = fields.Many2one("subscription.plan", string="New Plan")
    old_amount = fields.Monetary(currency_field="currency_id")
    new_amount = fields.Monetary(currency_field="currency_id")
    reason = fields.Char()
    notes = fields.Text()
