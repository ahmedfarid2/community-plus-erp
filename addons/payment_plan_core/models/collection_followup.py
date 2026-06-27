from odoo import api, fields, models


class CollectionFollowup(models.Model):
    _name = "collection.followup"
    _description = "Collection Follow-up"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "followup_date desc, id desc"
    _rec_name = "display_name"

    partner_id = fields.Many2one(
        "res.partner", string="Customer", required=True, tracking=True)
    plan_id = fields.Many2one(
        "payment.plan", string="Payment Plan", ondelete="cascade", index=True)
    line_id = fields.Many2one(
        "payment.plan.line", string="Payment Line", ondelete="set null",
        help="Optional specific installment this follow-up is about.")
    company_id = fields.Many2one(
        "res.company", string="Company", required=True,
        default=lambda self: self.env.company)

    followup_date = fields.Date(
        string="Follow-up Date", default=fields.Date.context_today,
        required=True, tracking=True)
    followup_type = fields.Selection(
        [("call", "Call"),
         ("whatsapp", "WhatsApp"),
         ("email", "Email"),
         ("meeting", "Meeting"),
         ("note", "Note"),
         ("other", "Other")],
        string="Type", default="call", required=True, tracking=True)
    assigned_to = fields.Many2one(
        "res.users", string="Assigned To", tracking=True,
        default=lambda self: self.env.user)
    status = fields.Selection(
        [("planned", "Planned"),
         ("done", "Done"),
         ("cancelled", "Cancelled")],
        string="Status", default="planned", required=True, tracking=True)
    notes = fields.Text(string="Notes")
    next_action_date = fields.Date(
        string="Next Action Date",
        help="When the next follow-up should happen, if any.")

    display_name = fields.Char(compute="_compute_display_name", store=True)

    @api.depends("partner_id", "followup_type", "followup_date")
    def _compute_display_name(self):
        type_labels = dict(self._fields["followup_type"].selection)
        for rec in self:
            parts = [rec.partner_id.display_name or "Follow-up"]
            if rec.followup_type:
                parts.append(type_labels.get(rec.followup_type, ""))
            if rec.followup_date:
                parts.append(str(rec.followup_date))
            rec.display_name = " · ".join(p for p in parts if p)

    @api.onchange("plan_id")
    def _onchange_plan_id(self):
        if self.plan_id and not self.partner_id:
            self.partner_id = self.plan_id.partner_id

    def action_mark_done(self):
        self.write({"status": "done"})

    def action_cancel(self):
        self.write({"status": "cancelled"})
