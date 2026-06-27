from odoo import api, fields, models
from odoo.exceptions import UserError

RISK_SCORE = {"low": 90.0, "medium": 70.0, "high": 40.0, "blocked": 0.0}


class ProcurementVendorQuote(models.Model):
    _name = "procurement.vendor.quote"
    _description = "Vendor Quote"
    _inherit = ["mail.thread", "mail.activity.mixin", "procurement.audit.mixin"]
    _order = "total_score desc, total_amount, id"

    name = fields.Char(string="Reference", required=True, copy=False,
                       readonly=True, default=lambda s: "New")
    rfq_event_id = fields.Many2one("procurement.rfq.event", string="RFQ Event",
                                   required=True, ondelete="cascade", index=True)
    vendor_id = fields.Many2one("res.partner", string="Vendor", required=True)
    vendor_profile_id = fields.Many2one("procurement.vendor.profile",
                                        compute="_compute_profile", store=True)
    currency_id = fields.Many2one(
        "res.currency", default=lambda s: s.env.company.currency_id)
    quote_date = fields.Date(default=fields.Date.context_today)
    validity_date = fields.Date()
    delivery_date = fields.Date()
    payment_terms = fields.Char()
    quote_line_ids = fields.One2many("procurement.vendor.quote.line", "quote_id",
                                     string="Lines")
    subtotal_amount = fields.Monetary(compute="_compute_amounts", store=True,
                                      currency_field="currency_id")
    discount_amount = fields.Monetary(currency_field="currency_id")
    tax_amount = fields.Monetary(currency_field="currency_id")
    total_amount = fields.Monetary(compute="_compute_amounts", store=True,
                                   currency_field="currency_id")

    price_score = fields.Float(compute="_compute_scores", store=True)
    delivery_score = fields.Float(compute="_compute_scores", store=True)
    quality_score = fields.Float(default=80.0)
    risk_score = fields.Float(compute="_compute_profile", store=True)
    total_score = fields.Float(compute="_compute_scores", store=True)

    state = fields.Selection(
        [("draft", "Draft"), ("submitted", "Submitted"),
         ("shortlisted", "Shortlisted"), ("rejected", "Rejected"),
         ("awarded", "Awarded"), ("cancelled", "Cancelled")],
        default="draft", required=True, tracking=True, index=True)
    is_recommended = fields.Boolean(compute="_compute_recommended")
    notes = fields.Text()

    @api.depends("vendor_id")
    def _compute_profile(self):
        Profile = self.env["procurement.vendor.profile"]
        for q in self:
            prof = Profile.search([("partner_id", "=", q.vendor_id.id)], limit=1)
            q.vendor_profile_id = prof
            q.risk_score = RISK_SCORE.get(prof.risk_level, 70.0) if prof else 70.0

    @api.depends("quote_line_ids.subtotal", "discount_amount", "tax_amount")
    def _compute_amounts(self):
        for q in self:
            q.subtotal_amount = sum(q.quote_line_ids.mapped("subtotal"))
            q.total_amount = q.subtotal_amount - q.discount_amount + q.tax_amount

    @api.depends("total_amount", "delivery_date", "quality_score", "risk_score",
                 "rfq_event_id.vendor_quote_ids.total_amount",
                 "rfq_event_id.vendor_quote_ids.delivery_date",
                 "rfq_event_id.evaluation_method")
    def _compute_scores(self):
        weights = self._criteria_weights()
        for q in self:
            peers = q.rfq_event_id.vendor_quote_ids.filtered(
                lambda x: x.state not in ("rejected", "cancelled")
                and x.total_amount > 0)
            # Price score: lowest total = 100
            totals = peers.mapped("total_amount")
            best = min(totals) if totals else 0.0
            q.price_score = round(best / q.total_amount * 100.0, 1) \
                if q.total_amount else 0.0
            # Delivery score: earliest delivery = 100
            dates = [x.delivery_date for x in peers if x.delivery_date]
            if q.delivery_date and dates:
                earliest = min(dates)
                latest = max(dates)
                span = (latest - earliest).days or 1
                q.delivery_score = round(
                    100.0 - (q.delivery_date - earliest).days / span * 40.0, 1)
            else:
                q.delivery_score = 80.0
            q.total_score = round(
                (q.price_score * weights["price"]
                 + q.delivery_score * weights["delivery"]
                 + q.quality_score * weights["quality"]
                 + q.risk_score * weights["risk"]) / (sum(weights.values()) or 1),
                1)

    def _criteria_weights(self):
        crit = self.env["procurement.evaluation.criteria"].search(
            [("active", "=", True)])
        weights = {c.code: c.weight_percent for c in crit}
        return {
            "price": weights.get("price", 40.0),
            "delivery": weights.get("delivery", 20.0),
            "quality": weights.get("quality", 25.0),
            "risk": weights.get("risk", 15.0),
        }

    @api.depends("rfq_event_id.best_quote_id")
    def _compute_recommended(self):
        for q in self:
            q.is_recommended = q.rfq_event_id.best_quote_id == q

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "procurement.vendor.quote") or "New"
        return super().create(vals_list)

    def action_submit(self):
        for q in self:
            if not q.quote_line_ids:
                raise UserError("Add quote lines before submitting.")
            q.state = "submitted"
            q._audit("quote_submitted", q.vendor_id.name)

    def action_shortlist(self):
        self.write({"state": "shortlisted"})
        self._audit("quote_shortlisted")

    def action_reject(self):
        self.write({"state": "rejected"})
        self._audit("quote_rejected")

    def action_award(self):
        self.ensure_one()
        return self.rfq_event_id.with_context(
            force_quote=self.id).action_create_award()

    def action_cancel(self):
        self.write({"state": "cancelled"})

    def action_reset_to_draft(self):
        self.write({"state": "draft"})


class ProcurementVendorQuoteLine(models.Model):
    _name = "procurement.vendor.quote.line"
    _description = "Vendor Quote Line"
    _order = "id"

    quote_id = fields.Many2one("procurement.vendor.quote", required=True,
                               ondelete="cascade", index=True)
    rfq_line_id = fields.Many2one("procurement.rfq.line", string="RFQ Line")
    currency_id = fields.Many2one(related="quote_id.currency_id")
    product_id = fields.Many2one("product.product", string="Product")
    description = fields.Char(required=True)
    quantity = fields.Float(default=1.0)
    unit_price = fields.Monetary(currency_field="currency_id")
    discount_percent = fields.Float(string="Discount (%)")
    subtotal = fields.Monetary(compute="_compute_subtotal", store=True,
                               currency_field="currency_id")
    delivery_days = fields.Integer()
    alternative_product = fields.Boolean(string="Alternative")
    notes = fields.Char()

    @api.depends("quantity", "unit_price", "discount_percent")
    def _compute_subtotal(self):
        for line in self:
            gross = line.quantity * line.unit_price
            line.subtotal = gross * (1 - (line.discount_percent or 0.0) / 100.0)
