from odoo import api, fields, models


class PlanningSlot(models.Model):
    _name = "planning.lite.slot"
    _description = "Planning Shift"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "start_datetime desc"

    name = fields.Char(string="Role / Note")
    employee_id = fields.Many2one("hr.employee", required=True, tracking=True)
    department_id = fields.Many2one(related="employee_id.department_id", store=True)
    start_datetime = fields.Datetime(required=True, default=fields.Datetime.now,
                                     tracking=True)
    end_datetime = fields.Datetime(required=True, tracking=True)
    allocated_hours = fields.Float(compute="_compute_hours", store=True)
    company_id = fields.Many2one("res.company", default=lambda s: s.env.company)
    state = fields.Selection(
        [("draft", "Draft"), ("published", "Published")],
        default="draft", required=True, tracking=True)

    @api.depends("start_datetime", "end_datetime")
    def _compute_hours(self):
        for slot in self:
            if slot.start_datetime and slot.end_datetime \
                    and slot.end_datetime > slot.start_datetime:
                delta = slot.end_datetime - slot.start_datetime
                slot.allocated_hours = delta.total_seconds() / 3600.0
            else:
                slot.allocated_hours = 0.0

    def action_publish(self):
        for slot in self:
            slot.state = "published"
            if slot.employee_id.user_id:
                slot.activity_schedule(
                    "mail.mail_activity_data_todo",
                    user_id=slot.employee_id.user_id.id,
                    summary="New shift: %s" % (slot.name or slot.start_datetime))

    def action_reset(self):
        self.write({"state": "draft"})
