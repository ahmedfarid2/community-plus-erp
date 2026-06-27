from odoo import api, fields, models
from odoo.exceptions import UserError


class Subscription(models.Model):
    _inherit = "subscription.subscription"

    invoice_count = fields.Integer(compute="_compute_invoice_count")

    @api.depends("billing_line_ids.invoice_id")
    def _compute_invoice_count(self):
        for sub in self:
            sub.invoice_count = len(sub.billing_line_ids.mapped("invoice_id"))

    def action_create_due_invoices(self):
        self.ensure_one()
        lines = self.billing_line_ids.filtered(
            lambda l: not l.invoice_id and l.state in ("due", "overdue"))
        if not lines:
            raise UserError("No due billing lines to invoice.")
        return lines.action_create_invoice()

    def action_view_invoices(self):
        self.ensure_one()
        moves = self.billing_line_ids.mapped("invoice_id")
        if not moves:
            raise UserError("No invoices generated yet.")
        action = {"type": "ir.actions.act_window", "name": "Invoices",
                  "res_model": "account.move", "context": {"create": False}}
        if len(moves) == 1:
            action.update(view_mode="form", res_id=moves.id)
        else:
            action.update(view_mode="list,form",
                          domain=[("id", "in", moves.ids)])
        return action
