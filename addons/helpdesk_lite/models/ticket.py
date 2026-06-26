from odoo import api, fields, models


class HelpdeskTeam(models.Model):
    _name = "helpdesk.lite.team"
    _description = "Helpdesk Team"
    _order = "name"

    name = fields.Char(required=True)
    user_id = fields.Many2one("res.users", string="Team Lead")
    member_ids = fields.Many2many("res.users", string="Members")
    active = fields.Boolean(default=True)


class HelpdeskTicket(models.Model):
    _name = "helpdesk.lite.ticket"
    _description = "Helpdesk Ticket"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "priority desc, create_date desc"

    name = fields.Char(required=True, tracking=True)
    team_id = fields.Many2one("helpdesk.lite.team", tracking=True)
    user_id = fields.Many2one("res.users", string="Assigned To", tracking=True)
    partner_id = fields.Many2one("res.partner", string="Customer")
    email_from = fields.Char()
    priority = fields.Selection(
        [("0", "Low"), ("1", "Normal"), ("2", "High"), ("3", "Urgent")],
        default="1",
        tracking=True,
    )
    state = fields.Selection(
        [
            ("new", "New"),
            ("in_progress", "In Progress"),
            ("waiting", "Waiting"),
            ("solved", "Solved"),
            ("cancelled", "Cancelled"),
        ],
        default="new",
        required=True,
        tracking=True,
    )
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company)
    description = fields.Html()
    resolution = fields.Html()
    deadline = fields.Datetime()

    def action_start(self):
        self.write({"state": "in_progress"})

    def action_waiting(self):
        self.write({"state": "waiting"})

    def action_solve(self):
        self.write({"state": "solved"})

    def action_cancel(self):
        self.write({"state": "cancelled"})

    def action_reopen(self):
        self.write({"state": "new"})

    def action_assign_to_me(self):
        self.write({"user_id": self.env.user.id})

    # ── Assignment behaviour ────────────────────────────────────────────────
    DONE_STATES = ("solved", "cancelled")

    def _schedule_assignee_activity(self):
        self.ensure_one()
        # Replace any existing to-do so the activity always points at the
        # current assignee.
        self.activity_unlink(["mail.mail_activity_data_todo"])
        if self.user_id and self.state not in self.DONE_STATES:
            self.activity_schedule(
                "mail.mail_activity_data_todo",
                user_id=self.user_id.id,
                summary="Handle ticket: %s" % self.name,
            )

    @api.model_create_multi
    def create(self, vals_list):
        tickets = super().create(vals_list)
        for ticket in tickets:
            # Default the assignee to the team lead when none is given.
            if not ticket.user_id and ticket.team_id.user_id:
                ticket.user_id = ticket.team_id.user_id
            ticket._schedule_assignee_activity()
        return tickets

    def write(self, vals):
        res = super().write(vals)
        if "user_id" in vals:
            for ticket in self:
                ticket._schedule_assignee_activity()
        if vals.get("state") in self.DONE_STATES:
            self.activity_unlink(["mail.mail_activity_data_todo"])
        return res
