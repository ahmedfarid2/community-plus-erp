import secrets

from odoo import api, fields, models


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
    access_token = fields.Char(
        string="Access Token", copy=False, index=True, groups="base.group_user",
        help="Secret token authenticating the approver's email/portal link.")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("access_token"):
                vals["access_token"] = secrets.token_urlsafe(32)
        return super().create(vals_list)

    def _portal_url(self):
        self.ensure_one()
        base = self.env["ir.config_parameter"].sudo().get_param(
            "web.base.url", "")
        return "%s/approval/act/%s?token=%s" % (
            base, self.id, self.access_token or "")
