from odoo import api, fields, models


class FsmOrder(models.Model):
    _name = "fsm.lite.order"
    _description = "Field Service Order"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "scheduled_date desc, id desc"

    name = fields.Char(required=True, default="New Service Order", tracking=True)
    partner_id = fields.Many2one("res.partner", string="Customer", required=True,
                                 tracking=True)
    address = fields.Char(related="partner_id.contact_address", string="Location")
    employee_id = fields.Many2one("hr.employee", string="Technician", tracking=True)
    scheduled_date = fields.Datetime(default=fields.Datetime.now, tracking=True)
    duration = fields.Float(string="Duration (h)", default=1.0)
    state = fields.Selection(
        [("new", "New"), ("planned", "Planned"), ("in_progress", "In Progress"),
         ("done", "Done"), ("cancel", "Cancelled")],
        default="new", required=True, tracking=True)
    worksheet = fields.Html(help="On-site report / work performed.")
    company_id = fields.Many2one("res.company", default=lambda s: s.env.company)

    def action_plan(self):
        for order in self:
            order.state = "planned"
            if order.employee_id.user_id:
                order.activity_schedule(
                    "mail.mail_activity_data_todo",
                    user_id=order.employee_id.user_id.id,
                    summary="Field service: %s" % (order.partner_id.name or order.name))

    def action_start(self):
        self.write({"state": "in_progress"})

    def action_done(self):
        self.write({"state": "done"})
        self.activity_unlink(["mail.mail_activity_data_todo"])

    def action_cancel(self):
        self.write({"state": "cancel"})

    def action_reset(self):
        self.write({"state": "new"})
