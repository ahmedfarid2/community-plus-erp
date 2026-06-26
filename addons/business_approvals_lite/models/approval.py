from odoo import fields, models
from odoo.exceptions import UserError


class ApprovalCategory(models.Model):
    _name = "business.approval.category"
    _description = "Approval Category"
    _order = "sequence, name"

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    default_approver_id = fields.Many2one("res.users", string="Default Approver")


class ApprovalRequest(models.Model):
    _name = "business.approval.request"
    _description = "Approval Request"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc, id desc"

    name = fields.Char(required=True, tracking=True)
    category_id = fields.Many2one("business.approval.category", required=True)
    requester_id = fields.Many2one(
        "res.users", default=lambda self: self.env.user, required=True, tracking=True)
    approver_id = fields.Many2one("res.users", tracking=True)
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company)
    currency_id = fields.Many2one(related="company_id.currency_id")
    amount = fields.Monetary()
    reference = fields.Char()
    description = fields.Text()
    date_needed = fields.Date()
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("approved", "Approved"),
            ("refused", "Refused"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        required=True,
        tracking=True,
    )

    def action_submit(self):
        for request in self:
            if not request.approver_id:
                request.approver_id = request.category_id.default_approver_id
            if not request.approver_id:
                raise UserError("Set an approver before submitting.")
            request.state = "submitted"
            request.activity_schedule(
                "mail.mail_activity_data_todo",
                user_id=request.approver_id.id,
                summary="Approval needed",
            )

    def action_approve(self):
        self.write({"state": "approved"})
        self.activity_unlink(["mail.mail_activity_data_todo"])

    def action_refuse(self):
        self.write({"state": "refused"})
        self.activity_unlink(["mail.mail_activity_data_todo"])

    def action_cancel(self):
        self.write({"state": "cancelled"})

    def action_reset(self):
        self.write({"state": "draft"})
