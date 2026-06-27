from odoo import fields, models


class InventoryMovementAnalysis(models.Model):
    _name = "inventory.movement.analysis"
    _description = "Inventory Movement Analysis"
    _order = "analysis_date desc, id desc"

    product_id = fields.Many2one("product.product", required=True, index=True)
    warehouse_id = fields.Many2one("stock.warehouse", index=True)
    company_id = fields.Many2one("res.company", default=lambda s: s.env.company)
    analysis_date = fields.Date(default=fields.Date.context_today)
    period_start = fields.Date()
    period_end = fields.Date()
    opening_qty = fields.Float()
    closing_qty = fields.Float()
    total_in_qty = fields.Float()
    total_out_qty = fields.Float()
    sales_qty = fields.Float()
    purchase_qty = fields.Float()
    adjustment_qty = fields.Float()
    transfer_in_qty = fields.Float()
    transfer_out_qty = fields.Float()
    average_daily_out_qty = fields.Float()
    movement_count = fields.Integer()
    abnormal_movement_detected = fields.Boolean()
    notes = fields.Text()
