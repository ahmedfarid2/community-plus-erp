from odoo import api, fields, models
from odoo.exceptions import UserError


class PaymentPlanLine(models.Model):
    _inherit = "payment.plan.line"

    invoice_id = fields.Many2one(
        "account.move", string="Invoice", copy=False,
        domain="[('move_type', '=', 'out_invoice')]",
        help="Customer invoice that bills this installment. The line's Paid "
             "Amount follows what is reconciled against it.")
    invoice_state = fields.Selection(
        related="invoice_id.state", string="Invoice Status")
    invoice_payment_state = fields.Selection(
        related="invoice_id.payment_state", string="Invoice Payment")

    def _amount_paid_on_invoice(self):
        """Reconciled amount on the linked invoice, in the plan currency."""
        self.ensure_one()
        inv = self.invoice_id
        if not inv or inv.state != "posted":
            return 0.0
        # amount_total - amount_residual = settled portion (invoice currency).
        paid = inv.amount_total - inv.amount_residual
        if inv.currency_id and self.currency_id and inv.currency_id != self.currency_id:
            paid = inv.currency_id._convert(
                paid, self.currency_id, inv.company_id,
                inv.invoice_date or fields.Date.context_today(self))
        return paid

    def action_sync_paid_from_invoice(self):
        """Pull the paid amount from the linked invoice onto the line."""
        for line in self.filtered("invoice_id"):
            paid = min(line.amount, line._amount_paid_on_invoice())
            if line.paid_amount != paid:
                line.with_context(allow_overpayment=True).paid_amount = paid
        return True

    def action_open_invoice(self):
        self.ensure_one()
        if not self.invoice_id:
            raise UserError("This line has no linked invoice yet.")
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "res_id": self.invoice_id.id,
            "view_mode": "form",
            "target": "current",
        }

    @api.model
    def _cron_sync_paid_from_invoices(self):
        """Daily: refresh paid amounts on lines that bill an open invoice."""
        lines = self.search([
            ("invoice_id", "!=", False),
            ("invoice_id.state", "=", "posted"),
            ("status", "not in", ("paid", "cancelled")),
        ])
        lines.action_sync_paid_from_invoice()
