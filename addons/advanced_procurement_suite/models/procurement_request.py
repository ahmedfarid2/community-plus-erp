from odoo import api, fields, models
from odoo.exceptions import UserError

PRIORITY = [("low", "Low"), ("medium", "Medium"), ("high", "High"),
            ("critical", "Critical")]


class ProcurementRequest(models.Model):
    _name = "procurement.request"
    _description = "Purchase Request"
    _inherit = ["mail.thread", "mail.activity.mixin", "procurement.audit.mixin"]
    _order = "create_date desc, id desc"

    name = fields.Char(string="Reference", required=True, copy=False,
                       readonly=True, index=True, default=lambda s: "New")
    requester_id = fields.Many2one("res.users", string="Requester",
                                   default=lambda s: s.env.user, tracking=True)
    responsible_user_id = fields.Many2one("res.users", string="Responsible")
    company_id = fields.Many2one("res.company", default=lambda s: s.env.company)
    currency_id = fields.Many2one(
        "res.currency", default=lambda s: s.env.company.currency_id)
    request_date = fields.Date(default=fields.Date.context_today)
    needed_by_date = fields.Date()
    priority = fields.Selection(PRIORITY, default="medium", tracking=True)
    request_type = fields.Selection(
        [("product", "Product"), ("service", "Service"), ("asset", "Asset"),
         ("project", "Project"), ("other", "Other")], default="product")
    line_ids = fields.One2many("procurement.request.line", "request_id",
                               string="Lines")
    estimated_total_amount = fields.Monetary(
        compute="_compute_total", store=True, currency_field="currency_id")
    state = fields.Selection(
        [("draft", "Draft"), ("submitted", "Submitted"),
         ("under_review", "Under Review"), ("rfq_created", "RFQ Created"),
         ("approved", "Approved"), ("rejected", "Rejected"),
         ("cancelled", "Cancelled"), ("completed", "Completed")],
        default="draft", required=True, tracking=True, index=True)
    justification = fields.Text()
    notes = fields.Text()
    rfq_event_id = fields.Many2one("procurement.rfq.event", string="RFQ Event",
                                   readonly=True)
    rfq_count = fields.Integer(compute="_compute_counts")
    audit_count = fields.Integer(compute="_compute_counts")

    @api.depends("line_ids.estimated_subtotal")
    def _compute_total(self):
        for req in self:
            req.estimated_total_amount = sum(
                req.line_ids.mapped("estimated_subtotal"))

    def _compute_counts(self):
        for req in self:
            req.rfq_count = 1 if req.rfq_event_id else 0
            req.audit_count = self.env["procurement.audit.log"].search_count(
                [("related_model", "=", "procurement.request"),
                 ("related_record_id", "=", req.id)])

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "procurement.request") or "New"
        reqs = super().create(vals_list)
        reqs._audit("request_created")
        return reqs

    def action_submit(self):
        for req in self:
            if not req.line_ids:
                raise UserError("Add at least one line before submitting.")
            req.state = "submitted"
            req._audit("submitted")

    def action_review(self):
        self.write({"state": "under_review"})
        self._audit("reviewed")

    def action_approve(self):
        self.write({"state": "approved"})

    def action_reject(self):
        self.write({"state": "rejected"})

    def action_cancel(self):
        self.write({"state": "cancelled"})
        self._audit("cancelled")

    def action_reset_to_draft(self):
        self.write({"state": "draft"})

    def action_create_rfq(self):
        self.ensure_one()
        if self.rfq_event_id:
            raise UserError("An RFQ event already exists for this request.")
        if not self.line_ids:
            raise UserError("Add lines before creating an RFQ.")
        rfq = self.env["procurement.rfq.event"].create({
            "request_id": self.id,
            "responsible_user_id": (self.responsible_user_id.id
                                    or self.env.uid),
            "currency_id": self.currency_id.id,
            "line_ids": [(0, 0, {
                "product_id": l.product_id.id, "description": l.description,
                "quantity": l.quantity, "uom_id": l.uom_id.id,
                "target_price": l.estimated_unit_price,
                "required_delivery_date": l.required_date,
            }) for l in self.line_ids],
        })
        self.write({"rfq_event_id": rfq.id, "state": "rfq_created"})
        self._audit("rfq_opened", "RFQ %s created" % rfq.name)
        return {"type": "ir.actions.act_window",
                "res_model": "procurement.rfq.event", "res_id": rfq.id,
                "view_mode": "form", "target": "current"}

    def action_view_rfq(self):
        self.ensure_one()
        return {"type": "ir.actions.act_window",
                "res_model": "procurement.rfq.event",
                "res_id": self.rfq_event_id.id, "view_mode": "form",
                "target": "current"}

    def action_view_audit(self):
        self.ensure_one()
        return {"type": "ir.actions.act_window", "name": "Audit Logs",
                "res_model": "procurement.audit.log", "view_mode": "list",
                "domain": [("related_model", "=", "procurement.request"),
                           ("related_record_id", "=", self.id)]}


class ProcurementRequestLine(models.Model):
    _name = "procurement.request.line"
    _description = "Purchase Request Line"
    _order = "id"

    request_id = fields.Many2one("procurement.request", required=True,
                                 ondelete="cascade", index=True)
    currency_id = fields.Many2one(related="request_id.currency_id")
    product_id = fields.Many2one("product.product", string="Product")
    description = fields.Char(required=True)
    quantity = fields.Float(default=1.0)
    uom_id = fields.Many2one("uom.uom", string="UoM")
    estimated_unit_price = fields.Monetary(currency_field="currency_id")
    estimated_subtotal = fields.Monetary(compute="_compute_subtotal",
                                         store=True, currency_field="currency_id")
    required_date = fields.Date()
    notes = fields.Char()

    @api.depends("quantity", "estimated_unit_price")
    def _compute_subtotal(self):
        for line in self:
            line.estimated_subtotal = line.quantity * line.estimated_unit_price

    @api.onchange("product_id")
    def _onchange_product(self):
        if self.product_id:
            self.description = self.product_id.display_name
            self.estimated_unit_price = self.product_id.standard_price
            self.uom_id = self.product_id.uom_id
