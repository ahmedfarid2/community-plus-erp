from odoo import api, fields, models
from odoo.exceptions import UserError


class FsmServiceRequest(models.Model):
    _name = "fsm.service.request"
    _description = "Field Service Request"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc, id desc"

    name = fields.Char(string="Reference", required=True, copy=False,
                       readonly=True, index=True, default=lambda s: "New")
    partner_id = fields.Many2one("res.partner", string="Customer",
                                 required=True, tracking=True)
    contact_name = fields.Char()
    contact_phone = fields.Char()
    contact_email = fields.Char()
    service_location_id = fields.Many2one("fsm.service.location",
                                          string="Service Location")
    asset_id = fields.Many2one("fsm.customer.asset", string="Asset")
    service_type_id = fields.Many2one("fsm.service.type", string="Service Type")
    priority = fields.Selection(
        [("0", "Low"), ("1", "Medium"), ("2", "High"), ("3", "Critical")],
        default="1", tracking=True)
    description = fields.Text()
    requested_date = fields.Datetime(default=fields.Datetime.now)
    preferred_date = fields.Datetime()
    source = fields.Selection(
        [("phone", "Phone"), ("email", "Email"), ("whatsapp", "WhatsApp"),
         ("website", "Website"), ("internal", "Internal"), ("other", "Other")],
        default="phone")
    state = fields.Selection(
        [("new", "New"), ("reviewed", "Reviewed"), ("converted", "Converted"),
         ("rejected", "Rejected"), ("cancelled", "Cancelled")],
        default="new", required=True, tracking=True)
    work_order_id = fields.Many2one("fsm.work.order", string="Work Order",
                                    readonly=True)
    responsible_user_id = fields.Many2one("res.users", string="Responsible",
                                          default=lambda s: s.env.user)
    company_id = fields.Many2one("res.company", default=lambda s: s.env.company)
    notes = fields.Text()

    @api.onchange("partner_id")
    def _onchange_partner(self):
        if self.partner_id:
            self.contact_name = self.partner_id.name
            self.contact_phone = self.partner_id.phone
            self.contact_email = self.partner_id.email

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "fsm.service.request") or "New"
        return super().create(vals_list)

    def action_review(self):
        self.write({"state": "reviewed"})

    def action_reject(self):
        self.write({"state": "rejected"})

    def action_cancel(self):
        self.write({"state": "cancelled"})

    def action_reset_to_new(self):
        self.write({"state": "new"})

    def action_convert_to_work_order(self):
        self.ensure_one()
        if self.work_order_id:
            raise UserError("This request was already converted (%s)."
                            % self.work_order_id.name)
        wo = self.env["fsm.work.order"].create({
            "service_request_id": self.id,
            "partner_id": self.partner_id.id,
            "service_location_id": self.service_location_id.id,
            "asset_id": self.asset_id.id,
            "service_type_id": self.service_type_id.id,
            "priority": self.priority,
            "scheduled_start": self.preferred_date,
            "diagnosis": self.description,
        })
        self.write({"state": "converted", "work_order_id": wo.id})
        return {"type": "ir.actions.act_window", "res_model": "fsm.work.order",
                "res_id": wo.id, "view_mode": "form", "target": "current"}

    def action_view_work_order(self):
        self.ensure_one()
        return {"type": "ir.actions.act_window", "res_model": "fsm.work.order",
                "res_id": self.work_order_id.id, "view_mode": "form",
                "target": "current"}
