from odoo import fields, models


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
