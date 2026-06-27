from odoo import fields, models
from odoo.exceptions import UserError


class ProcurementAward(models.Model):
    _inherit = "procurement.award"

    purchase_order_id = fields.Many2one("purchase.order", string="Purchase Order",
                                        copy=False, readonly=True)

    def action_convert_to_po(self):
        self.ensure_one()
        if self.purchase_order_id:
            return self.action_view_purchase_order()
        if self.state != "approved":
            raise UserError("Approve the award before converting it to a PO.")
        missing = self.award_line_ids.filtered(lambda l: not l.product_id)
        if missing:
            raise UserError(
                "Converting to a purchase order needs a product on every award "
                "line. Missing on:\n• "
                + "\n• ".join(missing.mapped("description")))
        order = self.env["purchase.order"].create({
            "partner_id": self.vendor_id.id,
            "origin": "%s / %s" % (self.rfq_event_id.name, self.name),
            "order_line": [(0, 0, {
                "product_id": line.product_id.id,
                "name": line.description or line.product_id.display_name,
                "product_qty": line.awarded_quantity,
                "price_unit": line.unit_price,
                "date_planned": fields.Datetime.now(),
            }) for line in self.award_line_ids],
        })
        self.write({"purchase_order_id": order.id, "state": "converted_to_po"})
        self._audit("po_created", "PO %s created" % order.name)
        return self.action_view_purchase_order()

    def action_view_purchase_order(self):
        self.ensure_one()
        if not self.purchase_order_id:
            raise UserError("No purchase order linked yet.")
        return {"type": "ir.actions.act_window", "res_model": "purchase.order",
                "res_id": self.purchase_order_id.id, "view_mode": "form",
                "target": "current"}
