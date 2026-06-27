from odoo import fields, models


class ApprovalRequestLine(models.Model):
    _name = "approval.request.line"
    _description = "Approval Request Line"
    _order = "id"

    request_id = fields.Many2one(
        "approval.request", string="Request", required=True,
        ondelete="cascade", index=True)
    step_id = fields.Many2one("approval.workflow.step", string="Step")
    step_name = fields.Char(related="step_id.name", store=True, string="Step")
    approver_id = fields.Many2one("res.users", string="Approver")
    action = fields.Selection(
        [("pending", "Pending"),
         ("approved", "Approved"),
         ("rejected", "Rejected")],
        string="Action", default="pending", required=True)
    action_date = fields.Datetime(string="Action Date")
    comment = fields.Text()
    request_state = fields.Selection(
        related="request_id.state", string="Request Status")
    company_id = fields.Many2one(
        related="request_id.company_id", store=True)
