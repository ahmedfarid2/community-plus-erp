from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class ProcurementVendorContract(models.Model):
    _name = "procurement.vendor.contract"
    _description = "Vendor Contract"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "end_date, id"

    name = fields.Char(required=True, copy=False, readonly=True,
                       default=lambda s: "New", tracking=True)
    vendor_id = fields.Many2one("res.partner", string="Vendor", required=True,
                                tracking=True)
    company_id = fields.Many2one("res.company", default=lambda s: s.env.company)
    contract_type = fields.Char()
    start_date = fields.Date(default=fields.Date.context_today)
    end_date = fields.Date(tracking=True)
    renewal_date = fields.Date()
    contract_value = fields.Monetary(currency_field="currency_id")
    currency_id = fields.Many2one(
        "res.currency", default=lambda s: s.env.company.currency_id)
    payment_terms = fields.Char()
    sla_terms = fields.Text()
    auto_renew = fields.Boolean()
    responsible_user_id = fields.Many2one("res.users",
                                          default=lambda s: s.env.user)
    state = fields.Selection(
        [("draft", "Draft"), ("active", "Active"),
         ("expiring_soon", "Expiring Soon"), ("expired", "Expired"),
         ("renewed", "Renewed"), ("cancelled", "Cancelled")],
        default="draft", required=True, tracking=True)
    notes = fields.Text()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "procurement.vendor.contract") or "New"
        return super().create(vals_list)

    def action_activate(self):
        self.write({"state": "active"})

    def action_renew(self):
        for c in self:
            if c.end_date:
                c.end_date = c.end_date + relativedelta(years=1)
            if c.renewal_date:
                c.renewal_date = c.renewal_date + relativedelta(years=1)
            c.state = "active"
            c.message_post(body="Contract renewed.")

    def action_expire(self):
        self.write({"state": "expired"})

    def action_cancel(self):
        self.write({"state": "cancelled"})

    def action_view_vendor(self):
        self.ensure_one()
        profile = self.env["procurement.vendor.profile"].search(
            [("partner_id", "=", self.vendor_id.id)], limit=1)
        return {"type": "ir.actions.act_window",
                "res_model": "procurement.vendor.profile",
                "res_id": profile.id, "view_mode": "form", "target": "current"}

    @api.model
    def _cron_contract_reminders(self):
        today = fields.Date.context_today(self)
        for c in self.search([("state", "in", ("active", "expiring_soon")),
                              ("end_date", "!=", False)]):
            check_date = c.renewal_date or c.end_date
            soon = check_date - relativedelta(days=30)
            if today >= soon and c.state == "active":
                c.state = "expiring_soon"
            if c.end_date < today and c.state != "expired":
                c.state = "expired"
            elif c.state == "expiring_soon" and not c.activity_ids.filtered(
                    lambda a: a.summary == "Contract renewal: %s" % c.name):
                c.activity_schedule(
                    "mail.mail_activity_data_todo", date_deadline=check_date,
                    user_id=c.responsible_user_id.id or c.env.uid,
                    summary="Contract renewal: %s" % c.name,
                    note="Vendor contract with %s is expiring." % c.vendor_id.name)
