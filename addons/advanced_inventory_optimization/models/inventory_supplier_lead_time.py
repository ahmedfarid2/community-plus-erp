from odoo import api, fields, models


class InventorySupplierLeadTime(models.Model):
    _name = "inventory.supplier.lead.time"
    _description = "Supplier Lead Time"
    _order = "product_id, vendor_id"

    product_id = fields.Many2one("product.product", string="Product",
                                 required=True)
    vendor_id = fields.Many2one("res.partner", string="Vendor", required=True)
    company_id = fields.Many2one("res.company", default=lambda s: s.env.company)
    average_lead_time_days = fields.Float(default=7.0)
    minimum_lead_time_days = fields.Float()
    maximum_lead_time_days = fields.Float()
    last_delivery_date = fields.Date()
    deliveries_count = fields.Integer()
    reliability_score = fields.Float(default=80.0,
        help="0-100; higher = more reliable lead times.")
    notes = fields.Text()

    _prod_vendor_uniq = models.Constraint(
        "unique(product_id, vendor_id, company_id)",
        "A lead-time record already exists for this product/vendor.")
