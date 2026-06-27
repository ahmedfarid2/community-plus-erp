from odoo import fields, models


class InventoryOptimizationLog(models.Model):
    _name = "inventory.optimization.log"
    _description = "Inventory Optimization Log"
    _order = "event_date desc, id desc"

    event_type = fields.Selection(
        [("analysis_run", "Analysis Run"), ("alert_created", "Alert Created"),
         ("recommendation_created", "Recommendation Created"),
         ("recommendation_approved", "Recommendation Approved"),
         ("recommendation_rejected", "Recommendation Rejected"),
         ("converted_to_po", "Converted to PO"),
         ("dead_stock_review_created", "Dead Stock Review Created"),
         ("note", "Note")], string="Event", required=True)
    event_date = fields.Datetime(default=fields.Datetime.now)
    user_id = fields.Many2one("res.users", default=lambda s: s.env.user)
    related_model = fields.Char()
    related_record_id = fields.Integer()
    product_id = fields.Many2one("product.product")
    warehouse_id = fields.Many2one("stock.warehouse")
    description = fields.Char()
    notes = fields.Text()


class InventoryLogMixin(models.AbstractModel):
    _name = "inventory.log.mixin"
    _description = "Inventory Log Mixin"

    def _log(self, event_type, description=None):
        Log = self.env["inventory.optimization.log"]
        for rec in self:
            product = rec.product_id if "product_id" in rec._fields else False
            warehouse = rec.warehouse_id if "warehouse_id" in rec._fields else False
            Log.create({
                "event_type": event_type, "related_model": rec._name,
                "related_record_id": rec.id, "description": description or "",
                "product_id": product.id if product else False,
                "warehouse_id": warehouse.id if warehouse else False,
            })
