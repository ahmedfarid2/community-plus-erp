from odoo import api, fields, models
from odoo.exceptions import UserError


class ProcurementAward(models.Model):
    _name = "procurement.award"
    _description = "Procurement Award"
    _inherit = ["mail.thread", "mail.activity.mixin", "procurement.audit.mixin"]
    _order = "create_date desc, id desc"

    name = fields.Char(string="Reference", required=True, copy=False,
                       readonly=True, default=lambda s: "New")
    rfq_event_id = fields.Many2one("procurement.rfq.event", string="RFQ Event",
                                   required=True, ondelete="cascade", index=True)
    vendor_quote_id = fields.Many2one("procurement.vendor.quote",
                                      string="Vendor Quote")
    vendor_id = fields.Many2one("res.partner", string="Vendor", required=True)
    currency_id = fields.Many2one(related="rfq_event_id.currency_id")
    award_line_ids = fields.One2many("procurement.award.line", "award_id",
                                     string="Award Lines")
    award_date = fields.Date(default=fields.Date.context_today)
    awarded_by = fields.Many2one("res.users", default=lambda s: s.env.user)
    total_awarded_amount = fields.Monetary(compute="_compute_total", store=True,
                                           currency_field="currency_id")
    estimated_total = fields.Monetary(
        related="rfq_event_id.request_id.estimated_total_amount",
        currency_field="currency_id")
    savings_amount = fields.Monetary(compute="_compute_savings", store=True,
                                     currency_field="currency_id")
    approval_state = fields.Selection(
        [("not_required", "Not Required"), ("pending", "Pending"),
         ("approved", "Approved"), ("rejected", "Rejected")],
        default="not_required", tracking=True)
    state = fields.Selection(
        [("draft", "Draft"), ("pending_approval", "Pending Approval"),
         ("approved", "Approved"), ("converted_to_po", "Converted to PO"),
         ("cancelled", "Cancelled")], default="draft", required=True,
        tracking=True, index=True)
    risk_warning = fields.Char(compute="_compute_risk_warning")
    notes = fields.Text()

    @api.depends("award_line_ids.subtotal")
    def _compute_total(self):
        for a in self:
            a.total_awarded_amount = sum(a.award_line_ids.mapped("subtotal"))

    @api.depends("total_awarded_amount", "estimated_total", "state")
    def _compute_savings(self):
        for a in self:
            a.savings_amount = (a.estimated_total - a.total_awarded_amount) \
                if a.state in ("approved", "converted_to_po") else 0.0

    @api.depends("vendor_id")
    def _compute_risk_warning(self):
        Profile = self.env["procurement.vendor.profile"]
        for a in self:
            prof = Profile.search([("partner_id", "=", a.vendor_id.id)], limit=1)
            if prof and prof.risk_level in ("high", "blocked"):
                a.risk_warning = "Vendor risk level: %s" % dict(
                    prof._fields["risk_level"].selection).get(prof.risk_level)
            else:
                a.risk_warning = False

    @api.constrains("award_line_ids")
    def _check_over_award(self):
        allow = self.env["ir.config_parameter"].sudo().get_param(
            "procurement.allow_over_award") == "1"
        for a in self:
            for line in a.award_line_ids:
                if line.rfq_line_id and not allow and \
                        line.awarded_quantity > line.rfq_line_id.quantity:
                    raise UserError(
                        "Awarded qty (%s) exceeds requested (%s) on '%s'."
                        % (line.awarded_quantity, line.rfq_line_id.quantity,
                           line.description))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "procurement.award") or "New"
        awards = super().create(vals_list)
        awards._audit("award_created")
        return awards

    def action_request_approval(self):
        self.write({"state": "pending_approval", "approval_state": "pending"})
        self._audit("approval_requested")

    def action_approve(self):
        for a in self:
            prof = self.env["procurement.vendor.profile"].search(
                [("partner_id", "=", a.vendor_id.id)], limit=1)
            if prof and prof.risk_level == "blocked":
                raise UserError("Cannot approve an award to a blocked vendor.")
            a.write({"state": "approved", "approval_state": "approved"})
            if a.vendor_quote_id:
                a.vendor_quote_id.state = "awarded"
            a._audit("award_approved")

    def action_reject(self):
        self.write({"state": "draft", "approval_state": "rejected"})
        self._audit("award_rejected")

    def action_cancel(self):
        self.write({"state": "cancelled"})
        self._audit("cancelled")

    def action_view_audit(self):
        self.ensure_one()
        return {"type": "ir.actions.act_window", "name": "Audit Logs",
                "res_model": "procurement.audit.log", "view_mode": "list",
                "domain": [("related_model", "=", "procurement.award"),
                           ("related_record_id", "=", self.id)]}


class ProcurementAwardLine(models.Model):
    _name = "procurement.award.line"
    _description = "Award Line"
    _order = "id"

    award_id = fields.Many2one("procurement.award", required=True,
                               ondelete="cascade", index=True)
    currency_id = fields.Many2one(related="award_id.currency_id")
    rfq_line_id = fields.Many2one("procurement.rfq.line", string="RFQ Line")
    quote_line_id = fields.Many2one("procurement.vendor.quote.line",
                                    string="Quote Line")
    product_id = fields.Many2one("product.product", string="Product")
    description = fields.Char(required=True)
    awarded_quantity = fields.Float(default=1.0)
    unit_price = fields.Monetary(currency_field="currency_id")
    subtotal = fields.Monetary(compute="_compute_subtotal", store=True,
                               currency_field="currency_id")
    notes = fields.Char()

    @api.depends("awarded_quantity", "unit_price")
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.awarded_quantity * line.unit_price
