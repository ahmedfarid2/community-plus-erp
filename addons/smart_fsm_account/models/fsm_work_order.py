from odoo import api, fields, models
from odoo.exceptions import UserError


class FsmWorkOrder(models.Model):
    _inherit = "fsm.work.order"

    invoice_id = fields.Many2one("account.move", string="Invoice", copy=False,
                                 readonly=True)

    @api.depends("billable", "state", "invoice_id")
    def _compute_invoice_status(self):
        for wo in self:
            if wo.invoice_id:
                wo.invoice_status = "invoiced"
            elif not wo.billable or wo.state == "cancelled":
                wo.invoice_status = "not_billable"
            elif wo.state in ("completed", "reviewed"):
                wo.invoice_status = "to_invoice"
            else:
                wo.invoice_status = "not_billable"

    def _income_account(self):
        account = self.env["account.account"].search(
            [("account_type", "=", "income")], limit=1)
        if not account:
            raise UserError("No income account is configured.")
        return account

    def action_create_invoice(self):
        self.ensure_one()
        if self.invoice_id:
            return self.action_view_invoice()
        if self.state not in ("completed", "reviewed") or not self.billable:
            raise UserError(
                "Only completed, billable work orders can be invoiced.")
        account = self._income_account()
        lines = []
        for part in self.part_line_ids.filtered("billable"):
            line = {"name": part.description or (
                part.product_id.display_name if part.product_id else "Part"),
                "quantity": part.quantity, "price_unit": part.unit_price,
                "account_id": account.id, "tax_ids": [(6, 0, [])]}
            if part.product_id:
                line["product_id"] = part.product_id.id
            lines.append((0, 0, line))
        labor = sum(t.duration_hours * (t.technician_id.hourly_cost or 0.0)
                    for t in self.time_line_ids if t.billable)
        if labor:
            lines.append((0, 0, {
                "name": "Labor — %s" % self.name, "quantity": 1.0,
                "price_unit": labor, "account_id": account.id,
                "tax_ids": [(6, 0, [])]}))
        if not lines:
            raise UserError("No billable parts or labor to invoice.")
        move = self.env["account.move"].create({
            "move_type": "out_invoice", "partner_id": self.partner_id.id,
            "invoice_origin": self.name, "currency_id": self.currency_id.id,
            "invoice_line_ids": lines})
        self.invoice_id = move
        self._log("note", "Invoice %s created" % move.name)
        return self.action_view_invoice()

    def action_view_invoice(self):
        self.ensure_one()
        if not self.invoice_id:
            raise UserError("No invoice yet.")
        return {"type": "ir.actions.act_window", "res_model": "account.move",
                "res_id": self.invoice_id.id, "view_mode": "form",
                "target": "current"}
