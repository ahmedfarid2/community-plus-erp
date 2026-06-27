from odoo import api, fields, models
from odoo.exceptions import ValidationError


class PaymentPlanLine(models.Model):
    _name = "payment.plan.line"
    _description = "Payment Plan Line"
    _order = "due_date, sequence, id"

    plan_id = fields.Many2one(
        "payment.plan", string="Payment Plan", required=True,
        ondelete="cascade", index=True)
    sequence = fields.Integer(string="Sequence", default=10)
    partner_id = fields.Many2one(
        related="plan_id.partner_id", string="Customer", store=True)
    company_id = fields.Many2one(
        related="plan_id.company_id", string="Company", store=True)
    currency_id = fields.Many2one(
        related="plan_id.currency_id", string="Currency", store=True)
    responsible_user_id = fields.Many2one(
        related="plan_id.responsible_user_id", store=True)

    due_date = fields.Date(string="Due Date", required=True)
    amount = fields.Monetary(
        string="Amount", currency_field="currency_id", required=True,
        help="Scheduled amount for this installment.")
    paid_amount = fields.Monetary(
        string="Paid Amount", currency_field="currency_id",
        help="Amount collected so far for this line. Enter manually for MVP.")
    remaining_amount = fields.Monetary(
        string="Remaining", currency_field="currency_id",
        compute="_compute_remaining", store=True)

    status = fields.Selection(
        [("pending", "Pending"),
         ("due", "Due"),
         ("partial", "Partial"),
         ("paid", "Paid"),
         ("overdue", "Overdue"),
         ("cancelled", "Cancelled")],
        string="Status", compute="_compute_status", store=True, index=True)
    days_overdue = fields.Integer(
        string="Days Overdue", compute="_compute_status", store=True)
    cancelled = fields.Boolean(
        string="Cancelled", help="Manually cancel this single line.")
    notes = fields.Char(string="Notes")

    @api.depends("amount", "paid_amount")
    def _compute_remaining(self):
        for line in self:
            line.remaining_amount = line.amount - line.paid_amount

    @api.depends("due_date", "amount", "paid_amount", "remaining_amount",
                 "cancelled", "plan_id.state",
                 "plan_id.template_id.grace_period_days")
    def _compute_status(self):
        from datetime import timedelta
        today = fields.Date.context_today(self)
        for line in self:
            grace = line.plan_id.template_id.grace_period_days or 0
            line.days_overdue = 0

            # Days overdue is informative regardless of the bucket below.
            if line.due_date and line.due_date < today and line.remaining_amount > 0:
                line.days_overdue = (today - line.due_date).days

            # Resolve the status in priority order (matches the spec).
            if line.cancelled or line.plan_id.state == "cancelled":
                line.status = "cancelled"
            elif line.amount and line.remaining_amount <= 0:
                line.status = "paid"
            elif line.paid_amount > 0:
                line.status = "partial"
            elif not line.due_date:
                line.status = "pending"
            elif today > line.due_date + timedelta(days=grace):
                line.status = "overdue"
            elif line.due_date <= today:
                # Due today, or within the grace window after the due date.
                line.status = "due"
            else:
                line.status = "pending"

    @api.constrains("amount")
    def _check_amount(self):
        for line in self:
            if line.amount < 0:
                raise ValidationError("Amount cannot be negative.")

    @api.constrains("paid_amount", "amount")
    def _check_paid_amount(self):
        for line in self:
            if line.paid_amount < 0:
                raise ValidationError("Paid Amount cannot be negative.")
            # Block overpayment unless explicitly allowed via context.
            if (line.paid_amount > line.amount
                    and not self.env.context.get("allow_overpayment")):
                raise ValidationError(
                    "Paid Amount (%s) cannot exceed the line Amount (%s). "
                    "Adjust the amount or split the payment."
                    % (line.paid_amount, line.amount))

    def action_mark_paid(self):
        """Convenience: settle the line in full."""
        for line in self:
            line.paid_amount = line.amount

    def action_cancel_line(self):
        self.write({"cancelled": True})
