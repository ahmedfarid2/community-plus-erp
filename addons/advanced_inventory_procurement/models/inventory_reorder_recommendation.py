from odoo import fields, models
from odoo.exceptions import UserError


class InventoryReorderRecommendation(models.Model):
    _inherit = "inventory.reorder.recommendation"

    procurement_request_id = fields.Many2one(
        "procurement.request", string="Purchase Request", copy=False,
        readonly=True)

    def action_create_procurement_request(self):
        approved = self.filtered(lambda r: r.state == "approved")
        if not approved:
            raise UserError(
                "Approve the recommendation(s) before sourcing them.")
        new = approved.filtered(lambda r: not r.procurement_request_id)
        if not new:
            return self._open_request(approved[:1].procurement_request_id)
        request = self.env["procurement.request"].create({
            "request_type": "product",
            "priority": "high",
            "justification": "Auto-created from inventory reorder recommendations.",
            "line_ids": [(0, 0, {
                "product_id": rec.product_id.id,
                "description": rec.product_id.display_name,
                "quantity": rec.suggested_qty,
                "estimated_unit_price": rec.estimated_unit_cost,
            }) for rec in new],
        })
        new.write({"procurement_request_id": request.id, "state": "converted"})
        new._log("note", "Purchase request %s created" % request.name)
        return self._open_request(request)

    def _open_request(self, request):
        return {"type": "ir.actions.act_window",
                "res_model": "procurement.request", "res_id": request.id,
                "view_mode": "form", "target": "current"}

    def action_view_procurement_request(self):
        self.ensure_one()
        if not self.procurement_request_id:
            raise UserError("No purchase request linked yet.")
        return self._open_request(self.procurement_request_id)
