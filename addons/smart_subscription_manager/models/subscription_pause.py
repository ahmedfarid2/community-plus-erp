from odoo import fields, models


class SubscriptionPause(models.Model):
    _name = "subscription.pause"
    _description = "Subscription Pause"
    _order = "pause_start_date desc, id desc"

    subscription_id = fields.Many2one(
        "subscription.subscription", string="Subscription", required=True,
        ondelete="cascade", index=True)
    partner_id = fields.Many2one(
        related="subscription_id.partner_id", store=True, string="Customer")
    pause_start_date = fields.Date(string="Pause Start", required=True,
                                   default=fields.Date.context_today)
    pause_end_date = fields.Date(string="Pause End")
    reason = fields.Char()
    state = fields.Selection(
        [("scheduled", "Scheduled"), ("active", "Active"),
         ("completed", "Completed"), ("cancelled", "Cancelled")],
        default="active", required=True)
    created_by = fields.Many2one("res.users", string="Created By",
                                 default=lambda s: s.env.user)
    notes = fields.Text()
