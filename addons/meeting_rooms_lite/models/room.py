from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import UserError


class Room(models.Model):
    _name = "meeting.lite.room"
    _description = "Meeting Room"
    _order = "name"

    name = fields.Char(required=True)
    capacity = fields.Integer(default=4)
    location = fields.Char()
    active = fields.Boolean(default=True)


class Booking(models.Model):
    _name = "meeting.lite.booking"
    _description = "Room Booking"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "start_datetime desc"

    name = fields.Char(string="Subject", required=True, tracking=True)
    room_id = fields.Many2one("meeting.lite.room", required=True, tracking=True)
    organizer_id = fields.Many2one("res.users", string="Organizer",
                                   default=lambda s: s.env.user)
    attendee_ids = fields.Many2many("res.partner", string="Attendees")
    start_datetime = fields.Datetime(required=True, default=fields.Datetime.now,
                                     tracking=True)
    stop_datetime = fields.Datetime(required=True, tracking=True)
    state = fields.Selection(
        [("draft", "Draft"), ("confirmed", "Confirmed"), ("cancel", "Cancelled")],
        default="draft", required=True, tracking=True)
    company_id = fields.Many2one("res.company", default=lambda s: s.env.company)

    @api.onchange("start_datetime")
    def _onchange_start(self):
        if self.start_datetime and not self.stop_datetime:
            self.stop_datetime = self.start_datetime + relativedelta(hours=1)

    def _check_clash(self):
        self.ensure_one()
        return self.search_count([
            ("id", "!=", self.id), ("room_id", "=", self.room_id.id),
            ("state", "=", "confirmed"),
            ("start_datetime", "<", self.stop_datetime),
            ("stop_datetime", ">", self.start_datetime),
        ])

    def action_confirm(self):
        for bk in self:
            if bk.stop_datetime <= bk.start_datetime:
                raise UserError("End time must be after start time.")
            if bk._check_clash():
                raise UserError("Room '%s' is already booked for that time."
                                % bk.room_id.name)
            bk.state = "confirmed"

    def action_cancel(self):
        self.write({"state": "cancel"})

    def action_reset(self):
        self.write({"state": "draft"})
