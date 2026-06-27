from collections import defaultdict

from odoo import fields, models
from odoo.exceptions import UserError


class InventoryReorderRecommendation(models.Model):
    _inherit = "inventory.reorder.recommendation"

    purchase_order_id = fields.Many2one("purchase.order", string="Purchase Order",
                                        copy=False, readonly=True)

    def action_convert_to_po(self):
        approved = self.filtered(lambda r: r.state == "approved")
        if not approved:
            raise UserError("Approve the recommendation(s) before converting.")
        already = approved.filtered("purchase_order_id")
        approved = approved - already
        no_vendor = approved.filtered(lambda r: not r.vendor_id)
        if no_vendor:
            raise UserError(
                "Set a vendor before converting:\n• "
                + "\n• ".join(no_vendor.mapped("product_id.display_name")))
        # group by vendor -> one PO per vendor
        by_vendor = defaultdict(lambda: self.env["inventory.reorder.recommendation"])
        for rec in approved:
            by_vendor[rec.vendor_id] |= rec
        orders = self.env["purchase.order"]
        for vendor, recs in by_vendor.items():
            po = self.env["purchase.order"].create({
                "partner_id": vendor.id,
                "origin": ", ".join(recs.mapped("name")),
                "order_line": [(0, 0, {
                    "product_id": rec.product_id.id,
                    "name": rec.product_id.display_name,
                    "product_qty": rec.suggested_qty,
                    "price_unit": rec.estimated_unit_cost,
                    "date_planned": fields.Datetime.now(),
                }) for rec in recs],
            })
            recs.write({"purchase_order_id": po.id, "state": "converted"})
            recs._log("converted_to_po", "PO %s" % po.name)
            orders |= po
        if len(orders) == 1:
            return self.action_view_purchase_order()
        return {"type": "ir.actions.act_window", "name": "Purchase Orders",
                "res_model": "purchase.order", "view_mode": "list,form",
                "domain": [("id", "in", orders.ids)]}

    def action_view_purchase_order(self):
        self.ensure_one()
        if not self.purchase_order_id:
            raise UserError("No purchase order linked yet.")
        return {"type": "ir.actions.act_window", "res_model": "purchase.order",
                "res_id": self.purchase_order_id.id, "view_mode": "form",
                "target": "current"}
