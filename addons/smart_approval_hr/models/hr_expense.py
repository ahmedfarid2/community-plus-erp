from odoo import _, api, fields, models


class HrExpense(models.Model):
    _inherit = "hr.expense"

    # Prefixed with sa_ because hr.expense already ships native
    # `approval_state` / `approval_request_id` fields in Odoo 19.
    sa_approval_request_id = fields.Many2one(
        "approval.request", string="Workflow Approval Request", copy=False,
        readonly=True)
    sa_approval_state = fields.Selection(
        [("none", "No Approval Needed"),
         ("to_request", "To Request"),
         ("pending", "Pending Approval"),
         ("approved", "Approved"),
         ("rejected", "Rejected")],
        string="Workflow Approval", compute="_compute_sa_approval_state")

    def _approval_workflow(self):
        self.ensure_one()
        workflows = self.env["approval.workflow"].sudo().search(
            [("model_name", "=", "hr.expense"), ("active", "=", True)])
        return workflows.filtered(lambda w: w._matches(self))[:1]

    @api.depends("sa_approval_request_id", "sa_approval_request_id.state",
                 "total_amount", "state")
    def _compute_sa_approval_state(self):
        for exp in self:
            req = exp.sa_approval_request_id
            if not exp._approval_workflow():
                exp.sa_approval_state = "none"
            elif not req or req.state == "cancelled":
                exp.sa_approval_state = "to_request"
            elif req.state == "approved":
                exp.sa_approval_state = "approved"
            elif req.state == "rejected":
                exp.sa_approval_state = "rejected"
            else:
                exp.sa_approval_state = "pending"

    def _request_sa_approval(self, workflow):
        self.ensure_one()
        req = self.sa_approval_request_id
        if not req or req.state in ("rejected", "cancelled"):
            req = self.env["approval.request"].create_for_record(
                self, workflow=workflow)
            self.sa_approval_request_id = req
        return req

    def action_approve(self, *args, **kwargs):
        allowed = self.env["hr.expense"]
        need_approval = self.env["hr.expense"]
        for exp in self:
            workflow = exp._approval_workflow()
            approved = (exp.sa_approval_request_id
                        and exp.sa_approval_request_id.state == "approved")
            if not workflow or approved:
                allowed |= exp
            else:
                exp._request_sa_approval(workflow)
                need_approval |= exp
        res = True
        if allowed:
            res = super(HrExpense, allowed).action_approve(*args, **kwargs)
        if need_approval:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Approval required"),
                    "message": _(
                        "%s expense(s) need workflow approval before they can "
                        "be approved.") % len(need_approval),
                    "type": "warning",
                    "sticky": False,
                },
            }
        return res

    def action_view_sa_approval_request(self):
        self.ensure_one()
        if not self.sa_approval_request_id:
            return False
        return {
            "type": "ir.actions.act_window",
            "res_model": "approval.request",
            "res_id": self.sa_approval_request_id.id,
            "view_mode": "form",
            "target": "current",
        }
