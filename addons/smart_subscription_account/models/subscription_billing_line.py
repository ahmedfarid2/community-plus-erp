from odoo import api, fields, models
from odoo.exceptions import UserError


class SubscriptionBillingLine(models.Model):
    _inherit = "subscription.billing.line"

    invoice_id = fields.Many2one(
        "account.move", string="Invoice", copy=False, readonly=True,
        domain="[('move_type', '=', 'out_invoice')]")
    invoice_state = fields.Selection(
        related="invoice_id.state", string="Invoice Status")
    invoice_payment_state = fields.Selection(
        related="invoice_id.payment_state", string="Invoice Payment")

    def _income_account(self):
        account = self.env["account.account"].search(
            [("account_type", "=", "income")], limit=1)
        if not account:
            raise UserError(
                "No income account is configured. Set up your chart of "
                "accounts before invoicing.")
        return account

    def action_create_invoice(self):
        Move = self.env["account.move"]
        created = self.env["account.move"]
        for line in self:
            if line.invoice_id:
                continue
            if line.state in ("skipped", "cancelled"):
                continue
            sub = line.subscription_id
            account = line._income_account()
            move = Move.create({
                "move_type": "out_invoice",
                "partner_id": sub.partner_id.id,
                "currency_id": sub.currency_id.id,
                "invoice_date_due": line.due_date,
                "invoice_origin": sub.name,
                "invoice_line_ids": [(0, 0, {
                    "name": "%s — %s to %s" % (
                        sub.plan_id.name, line.period_start_date,
                        line.period_end_date or ""),
                    "quantity": 1.0,
                    "price_unit": line.total_amount,
                    "account_id": account.id,
                    "tax_ids": [(6, 0, [])],
                })],
            })
            line.invoice_id = move
            if line.state == "due":
                line.state = "invoiced"
            sub._log_event("invoice_created", notes="Invoice %s" % move.name)
            created |= move
        if not created:
            raise UserError("Nothing to invoice (already invoiced or skipped).")
        return self._action_open_moves(created)

    def _action_open_moves(self, moves):
        action = {"type": "ir.actions.act_window", "name": "Invoices",
                  "res_model": "account.move", "context": {"create": False}}
        if len(moves) == 1:
            action.update(view_mode="form", res_id=moves.id)
        else:
            action.update(view_mode="list,form",
                          domain=[("id", "in", moves.ids)])
        return action

    def action_open_invoice(self):
        self.ensure_one()
        if not self.invoice_id:
            raise UserError("No invoice linked to this billing line.")
        return self._action_open_moves(self.invoice_id)

    def _amount_paid_on_invoice(self):
        self.ensure_one()
        inv = self.invoice_id
        if not inv or inv.state != "posted":
            return 0.0
        paid = inv.amount_total - inv.amount_residual
        if (inv.currency_id and self.currency_id
                and inv.currency_id != self.currency_id):
            paid = inv.currency_id._convert(
                paid, self.currency_id, inv.company_id,
                inv.invoice_date or fields.Date.context_today(self))
        return paid

    def action_sync_from_invoice(self):
        for line in self.filtered("invoice_id"):
            paid = min(line.total_amount, line._amount_paid_on_invoice())
            vals = {"paid_amount": paid}
            if line.total_amount and paid >= line.total_amount:
                vals["state"] = "paid"
            elif paid > 0:
                vals["state"] = "partially_paid"
            line.with_context(subscription_allow_overpayment=True).write(vals)
        return True

    @api.model
    def _cron_sync_invoices(self):
        lines = self.search([
            ("invoice_id", "!=", False),
            ("invoice_id.state", "=", "posted"),
            ("state", "not in", ("paid", "skipped", "cancelled")),
        ])
        lines.action_sync_from_invoice()
