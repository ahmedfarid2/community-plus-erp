from odoo import fields, models


class CloseReason(models.Model):
    _name = "subscription.lite.close.reason"
    _description = "Subscription Close Reason"
    _order = "sequence, name"

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
