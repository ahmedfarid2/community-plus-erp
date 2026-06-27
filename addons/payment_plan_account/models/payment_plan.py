from odoo import api, fields, models
from odoo.exceptions import UserError


class PaymentPlan(models.Model):
    _inherit = "payment.plan"

    invoice_count = fields.Integer(compute="_compute_invoice_count")

    @api.depends("line_ids.invoice_id")
    def _compute_invoice_count(self):
        for plan in self:
            plan.invoice_count = len(plan.line_ids.mapped("invoice_id"))

    def _income_account(self):
        """Find a usable income account for generated invoice lines."""
        account = self.env["account.account"].search(
            [("account_type", "=", "income")], limit=1)
        if not account:
            raise UserError(
                "No income account is configured. Set up your chart of "
                "accounts before generating invoices.")
        return account

    def action_create_invoices(self):
        """Create one draft customer invoice per uninvoiced, unpaid line."""
        Move = self.env["account.move"]
        created = self.env["account.move"]
        for plan in self:
            account = plan._income_account()
            to_invoice = plan.line_ids.filtered(
                lambda l: not l.invoice_id
                and l.status not in ("paid", "cancelled")
                and l.remaining_amount > 0)
            if not to_invoice:
                continue
            for line in to_invoice:
                move = Move.create({
                    "move_type": "out_invoice",
                    "partner_id": plan.partner_id.id,
                    "currency_id": plan.currency_id.id,
                    "invoice_date_due": line.due_date,
                    "invoice_origin": plan.name,
                    "invoice_line_ids": [(0, 0, {
                        "name": "%s — installment due %s" % (
                            plan.name, line.due_date or ""),
                        "quantity": 1.0,
                        "price_unit": line.remaining_amount,
                        "account_id": account.id,
                        "tax_ids": [(6, 0, [])],
                    })],
                })
                line.invoice_id = move
                created |= move
        if not created:
            raise UserError(
                "Nothing to invoice — every line is already invoiced, paid or "
                "cancelled.")
        return self._action_open_moves(created)

    def _action_open_moves(self, moves):
        action = {
            "type": "ir.actions.act_window",
            "name": "Invoices",
            "res_model": "account.move",
            "context": {"create": False},
        }
        if len(moves) == 1:
            action.update(view_mode="form", res_id=moves.id)
        else:
            action.update(view_mode="list,form",
                          domain=[("id", "in", moves.ids)])
        return action

    def action_view_invoices(self):
        self.ensure_one()
        moves = self.line_ids.mapped("invoice_id")
        if not moves:
            raise UserError("No invoices have been generated for this plan yet.")
        return self._action_open_moves(moves)

    def action_sync_paid_from_invoices(self):
        self.ensure_one()
        self.line_ids.action_sync_paid_from_invoice()
        return True
