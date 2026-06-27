from odoo import api, fields, models
from odoo.exceptions import UserError


class ApprovalActionWizard(models.TransientModel):
    _name = "approval.action.wizard"
    _description = "Approve / Reject Wizard"

    request_id = fields.Many2one(
        "approval.request", string="Request", required=True)
    action = fields.Selection(
        [("approved", "Approve"), ("rejected", "Reject")],
        string="Action", required=True)
    comment = fields.Text(
        string="Comment",
        help="Optional for approvals, recommended for rejections.")

    @api.constrains("action", "comment")
    def _check_comment(self):
        for wiz in self:
            if wiz.action == "rejected" and not (wiz.comment or "").strip():
                raise UserError("Please give a reason for the rejection.")

    def action_confirm(self):
        self.ensure_one()
        self.request_id._act(self.action, self.comment)
        return {"type": "ir.actions.act_window_close"}
