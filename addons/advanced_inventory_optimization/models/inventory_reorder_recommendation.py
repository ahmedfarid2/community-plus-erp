from odoo import api, fields, models
from odoo.exceptions import UserError


class InventoryReorderRecommendation(models.Model):
    _name = "inventory.reorder.recommendation"
    _description = "Reorder Recommendation"
    _inherit = ["mail.thread", "mail.activity.mixin", "inventory.log.mixin"]
    _order = "priority desc, create_date desc, id desc"

    name = fields.Char(required=True, copy=False, readonly=True,
                       default=lambda s: "New")
    product_id = fields.Many2one("product.product", required=True, index=True)
    warehouse_id = fields.Many2one("stock.warehouse", index=True)
    company_id = fields.Many2one("res.company", default=lambda s: s.env.company)
    currency_id = fields.Many2one(
        "res.currency", default=lambda s: s.env.company.currency_id)
    vendor_id = fields.Many2one("res.partner", string="Vendor")

    current_qty = fields.Float()
    forecasted_qty = fields.Float()
    average_daily_demand = fields.Float()
    supplier_lead_time_days = fields.Float()
    safety_stock_qty = fields.Float()
    reorder_point_qty = fields.Float()
    suggested_qty = fields.Float()
    estimated_unit_cost = fields.Monetary(currency_field="currency_id")
    estimated_total_cost = fields.Monetary(compute="_compute_total",
                                           store=True, currency_field="currency_id")
    reason = fields.Selection(
        [("stockout_risk", "Stockout Risk"), ("low_stock", "Low Stock"),
         ("demand_increase", "Demand Increase"), ("manual", "Manual")],
        default="low_stock")
    priority = fields.Selection(
        [("low", "Low"), ("medium", "Medium"), ("high", "High"),
         ("critical", "Critical")], default="medium", index=True)
    state = fields.Selection(
        [("draft", "Draft"), ("recommended", "Recommended"),
         ("approved", "Approved"), ("rejected", "Rejected"),
         ("converted", "Converted"), ("cancelled", "Cancelled")],
        default="recommended", required=True, tracking=True, index=True)
    approved_by = fields.Many2one("res.users", readonly=True)
    approved_date = fields.Datetime(readonly=True)
    rejection_reason = fields.Char()
    notes = fields.Text()

    @api.depends("suggested_qty", "estimated_unit_cost")
    def _compute_total(self):
        for r in self:
            r.estimated_total_cost = r.suggested_qty * r.estimated_unit_cost

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "inventory.reorder.recommendation") or "New"
        recs = super().create(vals_list)
        recs._log("recommendation_created")
        return recs

    def action_approve(self):
        self.write({"state": "approved", "approved_by": self.env.uid,
                    "approved_date": fields.Datetime.now()})
        self._log("recommendation_approved")

    def action_reject(self):
        for r in self:
            if not r.rejection_reason:
                raise UserError(
                    "Provide a rejection reason before rejecting '%s'." % r.name)
            r.write({"state": "rejected"})
            r._log("recommendation_rejected")

    def action_cancel(self):
        self.write({"state": "cancelled"})

    def action_reset_to_draft(self):
        self.write({"state": "draft"})

    def action_view_product(self):
        self.ensure_one()
        return {"type": "ir.actions.act_window", "res_model": "product.product",
                "res_id": self.product_id.id, "view_mode": "form"}

    def action_view_vendor(self):
        self.ensure_one()
        return {"type": "ir.actions.act_window", "res_model": "res.partner",
                "res_id": self.vendor_id.id, "view_mode": "form"}
