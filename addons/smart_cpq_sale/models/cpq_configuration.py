from odoo import _, fields, models
from odoo.exceptions import UserError


class CpqConfiguration(models.Model):
    _inherit = "cpq.configuration"

    sale_order_id = fields.Many2one(
        "sale.order", string="Quotation", readonly=True, copy=False)

    def action_create_quotation(self):
        self.ensure_one()
        if self.state not in ("validated", "quoted"):
            raise UserError(_("Validate the configuration before quoting."))
        if not self.partner_id:
            raise UserError(_("Set a customer before creating a quotation."))
        unit_price = (self.total_price / self.quantity) if self.quantity \
            else self.total_price
        line_vals = {
            "name": self._quote_description(),
            "product_uom_qty": self.quantity,
            "price_unit": unit_price,
        }
        if self.template_id.base_product_id:
            line_vals["product_id"] = self.template_id.base_product_id.id
        order = self.env["sale.order"].create({
            "partner_id": self.partner_id.id,
            "origin": self.name,
            "order_line": [(0, 0, line_vals)],
        })
        self.write({"sale_order_id": order.id, "state": "quoted"})
        return {
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            "res_id": order.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_view_sale_order(self):
        self.ensure_one()
        if not self.sale_order_id:
            return False
        return {
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            "res_id": self.sale_order_id.id,
            "view_mode": "form",
            "target": "current",
        }
