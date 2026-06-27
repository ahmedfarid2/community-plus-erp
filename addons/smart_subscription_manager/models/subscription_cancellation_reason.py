from odoo import fields, models


class SubscriptionCancellationReason(models.Model):
    _name = "subscription.cancellation.reason"
    _description = "Subscription Cancellation Reason"
    _order = "name"

    name = fields.Char(required=True, translate=True)
    code = fields.Char()
    active = fields.Boolean(default=True)
    notes = fields.Text()

    _code_uniq = models.Constraint(
        "unique(code)", "The cancellation reason code must be unique.")
