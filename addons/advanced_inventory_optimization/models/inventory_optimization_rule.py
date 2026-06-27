from odoo import fields, models


class InventoryOptimizationRule(models.Model):
    _name = "inventory.optimization.rule"
    _description = "Inventory Optimization Rule"
    _order = "sequence, id"

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    company_id = fields.Many2one("res.company", default=lambda s: s.env.company)
    warehouse_id = fields.Many2one("stock.warehouse", string="Warehouse")
    product_category_id = fields.Many2one("product.category", string="Category")
    active = fields.Boolean(default=True)

    analysis_period_days = fields.Integer(default=90,
        help="Look-back window for demand and movement analysis.")
    slow_moving_days = fields.Integer(default=90)
    dead_stock_days = fields.Integer(default=180)
    safety_stock_days = fields.Integer(default=7)
    minimum_stock_coverage_days = fields.Integer(default=14)
    maximum_stock_coverage_days = fields.Integer(default=120)
    default_supplier_lead_time_days = fields.Integer(default=7)
    reorder_rounding_method = fields.Selection(
        [("none", "None"), ("nearest_integer", "Nearest Integer"),
         ("pack_size", "Pack Size"), ("custom", "Custom")],
        default="nearest_integer", required=True)
    pack_size = fields.Float(default=1.0)

    alert_stockout = fields.Boolean(default=True)
    alert_overstock = fields.Boolean(default=True)
    alert_slow_moving = fields.Boolean(default=True)
    alert_dead_stock = fields.Boolean(default=True)
    alert_negative_stock = fields.Boolean(default=True)
    notes = fields.Text()

    def _round_qty(self, qty):
        self.ensure_one()
        if qty <= 0:
            return 0.0
        method = self.reorder_rounding_method
        if method == "nearest_integer":
            return float(round(qty))
        if method == "pack_size" and self.pack_size > 0:
            import math
            return math.ceil(qty / self.pack_size) * self.pack_size
        return qty
