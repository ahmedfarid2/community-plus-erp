from odoo import fields, models


class InventoryForecastProfile(models.Model):
    _name = "inventory.forecast.profile"
    _description = "Demand Forecast Profile"
    _order = "name"

    name = fields.Char(required=True, translate=True)
    company_id = fields.Many2one("res.company", default=lambda s: s.env.company)
    warehouse_id = fields.Many2one("stock.warehouse", string="Warehouse")
    product_category_id = fields.Many2one("product.category", string="Category")
    method = fields.Selection(
        [("moving_average", "Moving Average"),
         ("weighted_average", "Weighted Average"), ("manual", "Manual")],
        default="moving_average", required=True)
    period_days = fields.Integer(default=90)
    weight_recent_period = fields.Float(default=2.0,
        help="Weight given to the most recent half of the period.")
    seasonality_factor = fields.Float(default=1.0)
    active = fields.Boolean(default=True)
    notes = fields.Text()
