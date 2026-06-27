from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SubscriptionBillingLine(models.Model):
    _name = "subscription.billing.line"
    _description = "Subscription Billing Line"
    _order = "period_start_date, sequence, id"

    subscription_id = fields.Many2one(
        "subscription.subscription", string="Subscription", required=True,
        ondelete="cascade", index=True)
    partner_id = fields.Many2one(
        related="subscription_id.partner_id", store=True, string="Customer")
    currency_id = fields.Many2one(
        related="subscription_id.currency_id", string="Currency")
    sequence = fields.Integer(default=10)
    period_start_date = fields.Date(string="Period Start", required=True)
    period_end_date = fields.Date(string="Period End")
    billing_date = fields.Date()
    due_date = fields.Date()

    amount = fields.Monetary(currency_field="currency_id")
    discount_amount = fields.Monetary(currency_field="currency_id")
    tax_amount = fields.Monetary(currency_field="currency_id")
    total_amount = fields.Monetary(
        currency_field="currency_id", compute="_compute_amounts", store=True)
    paid_amount = fields.Monetary(currency_field="currency_id")
    remaining_amount = fields.Monetary(
        currency_field="currency_id", compute="_compute_amounts", store=True)

    state = fields.Selection(
        [("draft", "Draft"), ("due", "Due"), ("invoiced", "Invoiced"),
         ("partially_paid", "Partially Paid"), ("paid", "Paid"),
         ("overdue", "Overdue"), ("skipped", "Skipped"),
         ("cancelled", "Cancelled")],
        default="due", required=True, index=True)
    notes = fields.Char()

    _period_uniq = models.Constraint(
        "unique(subscription_id, period_start_date)",
        "A billing line already exists for this subscription and period.")

    @api.depends("amount", "discount_amount", "tax_amount", "paid_amount")
    def _compute_amounts(self):
        for line in self:
            line.total_amount = (line.amount - line.discount_amount
                                 + line.tax_amount)
            line.remaining_amount = line.total_amount - line.paid_amount

    @api.constrains("paid_amount", "amount")
    def _check_paid(self):
        allow = self.env["ir.config_parameter"].sudo().get_param(
            "subscription.allow_overpayment") == "1"
        for line in self:
            if line.paid_amount < 0:
                raise ValidationError("Paid amount cannot be negative.")
            if line.paid_amount > line.total_amount and not allow:
                raise ValidationError(
                    "Paid amount cannot exceed the total (%s)."
                    % line.total_amount)

    # --- payment actions ---
    def action_mark_paid(self):
        for line in self:
            line.write({"paid_amount": line.total_amount, "state": "paid"})

    def action_mark_partial(self):
        for line in self:
            line.state = "partially_paid"

    def action_mark_skipped(self):
        self.write({"state": "skipped"})

    def action_mark_cancelled(self):
        self.write({"state": "cancelled"})
