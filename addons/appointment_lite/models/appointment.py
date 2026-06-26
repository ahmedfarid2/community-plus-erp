from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class AppointmentType(models.Model):
    _name = "appointment.lite.type"
    _description = "Appointment Type"
    _order = "name"

    name = fields.Char(required=True)
    duration = fields.Float(string="Duration (h)", default=1.0, required=True)
    user_ids = fields.Many2many("res.users", string="Staff")
    active = fields.Boolean(default=True)


class AppointmentBooking(models.Model):
    _name = "appointment.lite.booking"
    _description = "Appointment Booking"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "start_datetime desc"

    name = fields.Char(compute="_compute_name", store=True)
    appointment_type_id = fields.Many2one("appointment.lite.type", required=True)
    partner_id = fields.Many2one("res.partner", string="Attendee", required=True,
                                 tracking=True)
    user_id = fields.Many2one("res.users", string="Staff",
                              default=lambda s: s.env.user, tracking=True)
    start_datetime = fields.Datetime(required=True, default=fields.Datetime.now,
                                     tracking=True)
    stop_datetime = fields.Datetime(compute="_compute_stop", store=True)
    state = fields.Selection(
        [("booked", "Booked"), ("confirmed", "Confirmed"),
         ("done", "Done"), ("cancel", "Cancelled")],
        default="booked", required=True, tracking=True)
    company_id = fields.Many2one("res.company", default=lambda s: s.env.company)
    note = fields.Text()

    @api.depends("appointment_type_id", "partner_id", "start_datetime")
    def _compute_name(self):
        for bk in self:
            parts = [bk.appointment_type_id.name or "Appointment"]
            if bk.partner_id:
                parts.append(bk.partner_id.name)
            bk.name = " - ".join(parts)

    @api.depends("start_datetime", "appointment_type_id.duration")
    def _compute_stop(self):
        for bk in self:
            if bk.start_datetime and bk.appointment_type_id:
                bk.stop_datetime = bk.start_datetime + relativedelta(
                    hours=int(bk.appointment_type_id.duration),
                    minutes=int((bk.appointment_type_id.duration % 1) * 60))
            else:
                bk.stop_datetime = bk.start_datetime

    def action_confirm(self):
        for bk in self:
            bk.state = "confirmed"
            if bk.user_id:
                bk.activity_schedule(
                    "mail.mail_activity_data_todo", user_id=bk.user_id.id,
                    date_deadline=bk.start_datetime,
                    summary="Appointment: %s" % (bk.partner_id.name or ""))

    def action_done(self):
        self.write({"state": "done"})
        self.activity_unlink(["mail.mail_activity_data_todo"])

    def action_cancel(self):
        self.write({"state": "cancel"})
