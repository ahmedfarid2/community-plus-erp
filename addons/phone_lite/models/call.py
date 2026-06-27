from odoo import api, fields, models


class PhoneCall(models.Model):
    _name = "phone.lite.call"
    _description = "Phone Call"
    _inherit = ["mail.thread"]
    _order = "call_date desc, id desc"

    name = fields.Char(compute="_compute_name", store=True)
    partner_id = fields.Many2one("res.partner", string="Contact")
    phone_number = fields.Char(required=True)
    direction = fields.Selection(
        [("outbound", "Outbound"), ("inbound", "Inbound")],
        default="outbound", required=True, tracking=True)
    state = fields.Selection(
        [("draft", "Planned"), ("done", "Completed"),
         ("missed", "Missed"), ("cancel", "Cancelled")],
        default="draft", required=True, tracking=True)
    call_date = fields.Datetime(default=fields.Datetime.now)
    duration = fields.Float(string="Duration (min)")
    user_id = fields.Many2one("res.users", string="Agent",
                              default=lambda s: s.env.user)
    company_id = fields.Many2one("res.company", default=lambda s: s.env.company)
    notes = fields.Text()

    @api.depends("partner_id", "phone_number", "direction")
    def _compute_name(self):
        for c in self:
            who = c.partner_id.name or c.phone_number or "Call"
            c.name = "%s — %s" % (dict(c._fields["direction"].selection).get(
                c.direction, ""), who)

    @api.onchange("partner_id")
    def _onchange_partner(self):
        if self.partner_id and not self.phone_number:
            self.phone_number = self.partner_id.mobile or self.partner_id.phone

    def action_done(self):
        self.write({"state": "done"})

    def action_missed(self):
        self.write({"state": "missed"})

    def action_cancel(self):
        self.write({"state": "cancel"})
