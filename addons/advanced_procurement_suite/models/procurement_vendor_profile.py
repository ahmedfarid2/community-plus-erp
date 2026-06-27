from odoo import api, fields, models


class ProcurementVendorCategory(models.Model):
    _name = "procurement.vendor.category"
    _description = "Vendor Category"
    _order = "name"

    name = fields.Char(required=True, translate=True)
    code = fields.Char()
    active = fields.Boolean(default=True)
    notes = fields.Text()


class ProcurementVendorProfile(models.Model):
    _name = "procurement.vendor.profile"
    _description = "Vendor Profile"
    _inherit = ["mail.thread"]
    _order = "total_score desc, id desc"
    _rec_name = "partner_id"

    partner_id = fields.Many2one("res.partner", string="Vendor", required=True,
                                 tracking=True)
    vendor_category_ids = fields.Many2many("procurement.vendor.category",
                                           string="Categories")
    preferred_vendor = fields.Boolean(string="Preferred", tracking=True)
    risk_level = fields.Selection(
        [("low", "Low"), ("medium", "Medium"), ("high", "High"),
         ("blocked", "Blocked")], default="low", required=True, tracking=True)
    quality_score = fields.Float(default=80.0)
    delivery_score = fields.Float(default=80.0)
    price_score = fields.Float(default=80.0)
    service_score = fields.Float(default=80.0)
    total_score = fields.Float(compute="_compute_total_score", store=True)
    payment_terms = fields.Char()
    currency_id = fields.Many2one(
        "res.currency", default=lambda s: s.env.company.currency_id)

    average_delivery_delay_days = fields.Float(compute="_compute_performance",
                                               store=True)
    on_time_delivery_rate = fields.Float(compute="_compute_performance",
                                         store=True, string="On-time %")
    total_orders_count = fields.Integer(compute="_compute_performance",
                                        store=True)
    total_spend = fields.Monetary(compute="_compute_spend", store=True,
                                  currency_field="currency_id")
    review_ids = fields.One2many("procurement.performance.review", "vendor_id",
                                 string="Reviews")
    active = fields.Boolean(default=True)
    notes = fields.Text()

    quote_count = fields.Integer(compute="_compute_counts")
    award_count = fields.Integer(compute="_compute_counts")
    contract_count = fields.Integer(compute="_compute_counts")
    review_count = fields.Integer(compute="_compute_counts")

    _partner_uniq = models.Constraint("unique(partner_id)",
                                      "A vendor profile already exists.")

    @api.depends("quality_score", "delivery_score", "price_score",
                 "service_score")
    def _compute_total_score(self):
        for v in self:
            v.total_score = round((v.quality_score + v.delivery_score
                                   + v.price_score + v.service_score) / 4.0, 1)

    @api.depends("review_ids.delivery_rating")
    def _compute_performance(self):
        for v in self:
            reviews = v.review_ids
            v.total_orders_count = len(reviews)
            if reviews:
                delays = reviews.mapped("delivery_delay_days")
                v.average_delivery_delay_days = sum(delays) / len(delays)
                on_time = len(reviews.filtered(
                    lambda r: (r.delivery_delay_days or 0) <= 0))
                v.on_time_delivery_rate = on_time / len(reviews) * 100.0
            else:
                v.average_delivery_delay_days = 0.0
                v.on_time_delivery_rate = 0.0

    @api.depends("partner_id")
    def _compute_spend(self):
        Award = self.env["procurement.award"]
        for v in self:
            awards = Award.search([("vendor_id", "=", v.partner_id.id),
                                   ("state", "in", ("approved",
                                                    "converted_to_po"))])
            v.total_spend = sum(awards.mapped("total_awarded_amount"))

    def _compute_counts(self):
        for v in self:
            v.quote_count = self.env["procurement.vendor.quote"].search_count(
                [("vendor_id", "=", v.partner_id.id)])
            v.award_count = self.env["procurement.award"].search_count(
                [("vendor_id", "=", v.partner_id.id)])
            v.contract_count = self.env["procurement.vendor.contract"].search_count(
                [("vendor_id", "=", v.partner_id.id)])
            v.review_count = len(v.review_ids)

    def action_view_quotes(self):
        self.ensure_one()
        return self._open("procurement.vendor.quote", "Quotes")

    def action_view_awards(self):
        self.ensure_one()
        return self._open("procurement.award", "Awards")

    def action_view_contracts(self):
        self.ensure_one()
        return self._open("procurement.vendor.contract", "Contracts")

    def action_view_reviews(self):
        self.ensure_one()
        return {"type": "ir.actions.act_window", "name": "Performance Reviews",
                "res_model": "procurement.performance.review",
                "view_mode": "list,form",
                "domain": [("vendor_id", "=", self.partner_id.id)],
                "context": {"default_vendor_id": self.partner_id.id}}

    def _open(self, model, name):
        return {"type": "ir.actions.act_window", "name": name,
                "res_model": model, "view_mode": "list,form",
                "domain": [("vendor_id", "=", self.partner_id.id)],
                "context": {"default_vendor_id": self.partner_id.id}}
