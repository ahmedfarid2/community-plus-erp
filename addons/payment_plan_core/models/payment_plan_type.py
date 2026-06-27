from odoo import fields, models


class PaymentPlanType(models.Model):
    _name = "payment.plan.type"
    _description = "Payment Plan Type"
    _order = "name"

    name = fields.Char(
        string="Name", required=True, translate=True,
        help="Human-readable category, e.g. Installments, Milestone Payments.")
    code = fields.Char(
        string="Code",
        help="Short technical code you can use in integrations or imports.")
    active = fields.Boolean(default=True)

    _code_uniq = models.Constraint(
        "unique(code)", "The plan type code must be unique.")
