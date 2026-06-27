from odoo import api, fields, models
from odoo.exceptions import UserError


class ProcurementRfqEvent(models.Model):
    _name = "procurement.rfq.event"
    _description = "RFQ Event"
    _inherit = ["mail.thread", "mail.activity.mixin", "procurement.audit.mixin"]
    _order = "create_date desc, id desc"

    name = fields.Char(string="Reference", required=True, copy=False,
                       readonly=True, index=True, default=lambda s: "New")
    request_id = fields.Many2one("procurement.request", string="Request",
                                 readonly=True)
    company_id = fields.Many2one("res.company", default=lambda s: s.env.company)
    responsible_user_id = fields.Many2one("res.users", string="Buyer",
                                          default=lambda s: s.env.user)
    currency_id = fields.Many2one(
        "res.currency", default=lambda s: s.env.company.currency_id)
    start_date = fields.Date(default=fields.Date.context_today)
    deadline_date = fields.Date(tracking=True)
    line_ids = fields.One2many("procurement.rfq.line", "rfq_event_id",
                               string="Lines", copy=True)
    invited_vendor_ids = fields.Many2many("res.partner", string="Invited Vendors")
    vendor_quote_ids = fields.One2many("procurement.vendor.quote",
                                       "rfq_event_id", string="Quotes")
    award_ids = fields.One2many("procurement.award", "rfq_event_id",
                                string="Awards")
    state = fields.Selection(
        [("draft", "Draft"), ("open", "Open"), ("closed", "Closed"),
         ("evaluation", "Evaluation"), ("awarded", "Awarded"),
         ("cancelled", "Cancelled")], default="draft", required=True,
        tracking=True, index=True)
    evaluation_method = fields.Selection(
        [("lowest_price", "Lowest Price"), ("weighted_score", "Weighted Score"),
         ("manual", "Manual")], default="weighted_score", required=True)
    estimated_total = fields.Monetary(related="request_id.estimated_total_amount",
                                      currency_field="currency_id")
    best_quote_id = fields.Many2one("procurement.vendor.quote",
                                    compute="_compute_best_quote",
                                    string="Recommended")
    quote_count = fields.Integer(compute="_compute_counts")
    award_count = fields.Integer(compute="_compute_counts")
    notes = fields.Text()

    @api.depends("vendor_quote_ids.total_score", "vendor_quote_ids.state",
                 "evaluation_method")
    def _compute_best_quote(self):
        for rfq in self:
            valid = rfq.vendor_quote_ids.filtered(
                lambda q: q.state in ("submitted", "shortlisted"))
            if not valid:
                rfq.best_quote_id = False
            elif rfq.evaluation_method == "lowest_price":
                rfq.best_quote_id = valid.sorted("total_amount")[:1]
            else:
                rfq.best_quote_id = valid.sorted("total_score",
                                                 reverse=True)[:1]

    def _compute_counts(self):
        for rfq in self:
            rfq.quote_count = len(rfq.vendor_quote_ids)
            rfq.award_count = len(rfq.award_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "procurement.rfq.event") or "New"
        return super().create(vals_list)

    def action_open(self):
        for rfq in self:
            if not rfq.line_ids:
                raise UserError("Add RFQ lines before opening.")
            if not rfq.invited_vendor_ids:
                raise UserError("Invite at least one vendor before opening.")
            rfq.state = "open"
            rfq._audit("rfq_opened")

    def action_invite_vendors(self):
        for rfq in self:
            for vendor in rfq.invited_vendor_ids:
                if not rfq.vendor_quote_ids.filtered(
                        lambda q: q.vendor_id == vendor):
                    self.env["procurement.vendor.quote"].create({
                        "rfq_event_id": rfq.id, "vendor_id": vendor.id,
                        "currency_id": rfq.currency_id.id,
                        "quote_line_ids": [(0, 0, {
                            "rfq_line_id": l.id, "product_id": l.product_id.id,
                            "description": l.description, "quantity": l.quantity,
                        }) for l in rfq.line_ids]})
                    rfq._audit("vendor_invited", vendor.name)
        return True

    def action_close(self):
        self.write({"state": "closed"})

    def action_start_evaluation(self):
        self.write({"state": "evaluation"})

    def action_generate_comparison(self):
        self.ensure_one()
        return {"type": "ir.actions.act_window", "name": "Quote Comparison",
                "res_model": "procurement.vendor.quote", "view_mode": "list,form",
                "domain": [("rfq_event_id", "=", self.id)],
                "context": {"default_rfq_event_id": self.id},
                "search_view_id": False}

    def action_create_award(self):
        self.ensure_one()
        if self.state not in ("evaluation", "closed") and \
                self.evaluation_method != "manual":
            raise UserError(
                "Start evaluation before awarding (or use Manual method).")
        forced = self.env.context.get("force_quote")
        quote = (self.vendor_quote_ids.browse(forced) if forced
                 else self.best_quote_id or self.vendor_quote_ids.filtered(
                     lambda q: q.state in ("submitted", "shortlisted"))[:1])
        if not quote:
            raise UserError("No submitted quote to award.")
        if quote.vendor_profile_id.risk_level == "blocked":
            raise UserError(
                "Vendor %s is blocked and cannot be awarded." % quote.vendor_id.name)
        award = self.env["procurement.award"].create({
            "rfq_event_id": self.id, "vendor_quote_id": quote.id,
            "vendor_id": quote.vendor_id.id,
            "award_line_ids": [(0, 0, {
                "rfq_line_id": ql.rfq_line_id.id, "quote_line_id": ql.id,
                "product_id": ql.product_id.id, "description": ql.description,
                "awarded_quantity": ql.quantity, "unit_price": ql.unit_price,
            }) for ql in quote.quote_line_ids],
        })
        self.write({"state": "awarded"})
        self._audit("award_created", "Award for %s" % quote.vendor_id.name)
        return {"type": "ir.actions.act_window",
                "res_model": "procurement.award", "res_id": award.id,
                "view_mode": "form", "target": "current"}

    def action_cancel(self):
        self.write({"state": "cancelled"})
        self._audit("cancelled")

    def action_reset_to_draft(self):
        self.write({"state": "draft"})

    def action_view_quotes(self):
        return self._open("procurement.vendor.quote", "Vendor Quotes")

    def action_view_awards(self):
        return self._open("procurement.award", "Awards")

    def action_view_audit(self):
        self.ensure_one()
        return {"type": "ir.actions.act_window", "name": "Audit Logs",
                "res_model": "procurement.audit.log", "view_mode": "list",
                "domain": [("related_model", "=", "procurement.rfq.event"),
                           ("related_record_id", "=", self.id)]}

    def _open(self, model, name):
        self.ensure_one()
        return {"type": "ir.actions.act_window", "name": name,
                "res_model": model, "view_mode": "list,form",
                "domain": [("rfq_event_id", "=", self.id)],
                "context": {"default_rfq_event_id": self.id}}


class ProcurementRfqLine(models.Model):
    _name = "procurement.rfq.line"
    _description = "RFQ Line"
    _order = "id"

    rfq_event_id = fields.Many2one("procurement.rfq.event", required=True,
                                   ondelete="cascade", index=True)
    currency_id = fields.Many2one(related="rfq_event_id.currency_id")
    product_id = fields.Many2one("product.product", string="Product")
    description = fields.Char(required=True)
    quantity = fields.Float(default=1.0)
    uom_id = fields.Many2one("uom.uom", string="UoM")
    target_price = fields.Monetary(currency_field="currency_id")
    required_delivery_date = fields.Date()
    notes = fields.Char()
