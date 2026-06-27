from odoo import api, fields, models


class ProcurementPerformanceReview(models.Model):
    _name = "procurement.performance.review"
    _description = "Vendor Performance Review"
    _inherit = ["mail.thread"]
    _order = "review_date desc, id desc"

    vendor_id = fields.Many2one("res.partner", string="Vendor", required=True)
    review_date = fields.Date(default=fields.Date.context_today)
    reviewed_by = fields.Many2one("res.users", default=lambda s: s.env.user)
    related_rfq_event_id = fields.Many2one("procurement.rfq.event",
                                           string="Related RFQ")
    quality_rating = fields.Float(default=80.0)
    delivery_rating = fields.Float(default=80.0)
    price_rating = fields.Float(default=80.0)
    service_rating = fields.Float(default=80.0)
    compliance_rating = fields.Float(default=80.0)
    delivery_delay_days = fields.Float(
        string="Delivery Delay (days)",
        help="Positive = late, 0 or negative = on time.")
    total_rating = fields.Float(compute="_compute_total", store=True)
    comments = fields.Text()

    @api.depends("quality_rating", "delivery_rating", "price_rating",
                 "service_rating", "compliance_rating")
    def _compute_total(self):
        for r in self:
            r.total_rating = round((r.quality_rating + r.delivery_rating
                                    + r.price_rating + r.service_rating
                                    + r.compliance_rating) / 5.0, 1)

    @api.model_create_multi
    def create(self, vals_list):
        reviews = super().create(vals_list)
        reviews._apply_to_profile()
        return reviews

    def write(self, vals):
        res = super().write(vals)
        self._apply_to_profile()
        return res

    def _apply_to_profile(self):
        """Update the vendor profile scores from the latest reviews."""
        Profile = self.env["procurement.vendor.profile"]
        for vendor in self.mapped("vendor_id"):
            profile = Profile.search([("partner_id", "=", vendor.id)], limit=1)
            if not profile:
                continue
            reviews = self.search([("vendor_id", "=", vendor.id)])
            if reviews:
                profile.write({
                    "quality_score": sum(reviews.mapped("quality_rating")) / len(reviews),
                    "delivery_score": sum(reviews.mapped("delivery_rating")) / len(reviews),
                    "price_score": sum(reviews.mapped("price_rating")) / len(reviews),
                    "service_score": sum(reviews.mapped("service_rating")) / len(reviews),
                })
