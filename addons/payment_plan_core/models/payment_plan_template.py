from odoo import api, fields, models
from odoo.exceptions import ValidationError


class PaymentPlanTemplate(models.Model):
    _name = "payment.plan.template"
    _description = "Payment Plan Template"
    _order = "name"

    name = fields.Char(
        string="Name", required=True, translate=True,
        help="e.g. 3 Monthly Payments, 50/50, 30/40/30 Milestones.")
    number_of_payments = fields.Integer(
        string="Number of Payments", default=1, required=True,
        help="How many installment lines this template generates.")
    frequency = fields.Selection(
        [("weekly", "Weekly"),
         ("monthly", "Monthly"),
         ("quarterly", "Quarterly"),
         ("custom", "Custom")],
        string="Frequency", default="monthly", required=True,
        help="Spacing between generated due dates. 'Custom' falls back to monthly "
             "spacing — refine the dates manually after generation.")
    first_payment_percent = fields.Float(
        string="First Payment %",
        help="Percentage of the total taken on the first line (e.g. 50 for a "
             "50/50 plan). Leave at 0 to split evenly.")
    equal_distribution = fields.Boolean(
        string="Equal Distribution", default=True,
        help="Split the total equally across all lines. Uncheck to use the "
             "First Payment % and distribute the remainder over the other lines.")
    grace_period_days = fields.Integer(
        string="Grace Period (days)", default=0,
        help="Days after a due date before the line is treated as overdue.")
    active = fields.Boolean(default=True)

    @api.constrains("number_of_payments")
    def _check_number_of_payments(self):
        for tmpl in self:
            if tmpl.number_of_payments < 1:
                raise ValidationError(
                    "Number of Payments must be at least 1.")

    @api.constrains("first_payment_percent")
    def _check_first_payment_percent(self):
        for tmpl in self:
            if not 0 <= tmpl.first_payment_percent <= 100:
                raise ValidationError(
                    "First Payment % must be between 0 and 100.")

    @api.constrains("grace_period_days")
    def _check_grace(self):
        for tmpl in self:
            if tmpl.grace_period_days < 0:
                raise ValidationError("Grace Period cannot be negative.")
