from odoo import api, fields, models


class Referral(models.Model):
    _name = "hr.referral.lite"
    _description = "Employee Referral"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc, id desc"

    name = fields.Char(string="Candidate", required=True, tracking=True)
    email = fields.Char()
    phone = fields.Char()
    referrer_id = fields.Many2one(
        "hr.employee", string="Referred By",
        default=lambda s: s.env.user.employee_id, tracking=True)
    job_id = fields.Many2one("hr.job", string="Job Position")
    company_id = fields.Many2one("res.company", default=lambda s: s.env.company)
    state = fields.Selection(
        [("new", "New"), ("interview", "Interview"),
         ("hired", "Hired"), ("refused", "Refused")],
        default="new", required=True, tracking=True)
    reward_points = fields.Integer(string="Reward Points", default=0)
    notes = fields.Text()

    def action_interview(self):
        self.write({"state": "interview"})

    def action_hire(self):
        # Award referral points on a successful hire.
        for ref in self:
            ref.state = "hired"
            if not ref.reward_points:
                ref.reward_points = 100
            ref.message_post(body="Candidate hired — %s reward points awarded to %s." % (
                ref.reward_points, ref.referrer_id.name or "referrer"))

    def action_refuse(self):
        self.write({"state": "refused"})

    def action_reset(self):
        self.write({"state": "new"})
