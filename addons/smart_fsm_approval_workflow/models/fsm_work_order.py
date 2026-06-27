from odoo import _, api, fields, models
from odoo.exceptions import UserError


class FsmWorkOrder(models.Model):
    _inherit = "fsm.work.order"

    approval_request_id = fields.Many2one(
        "approval.request", string="Approval Request", copy=False, readonly=True)
    approval_state = fields.Selection(
        [("none", "No Approval Needed"),
         ("to_request", "To Request"),
         ("pending", "Pending Approval"),
         ("approved", "Approved"),
         ("rejected", "Rejected")],
        string="Approval", compute="_compute_approval_state")

    def _approval_workflow(self):
        self.ensure_one()
        workflows = self.env["approval.workflow"].sudo().search(
            [("model_name", "=", "fsm.work.order"), ("active", "=", True)])
        return workflows.filtered(lambda w: w._matches(self))[:1]

    @api.depends("approval_request_id", "approval_request_id.state",
                 "cost_total", "billable_total", "state")
    def _compute_approval_state(self):
        for wo in self:
            req = wo.approval_request_id
            if not wo._approval_workflow():
                wo.approval_state = "none"
            elif not req or req.state == "cancelled":
                wo.approval_state = "to_request"
            elif req.state == "approved":
                wo.approval_state = "approved"
            elif req.state == "rejected":
                wo.approval_state = "rejected"
            else:
                wo.approval_state = "pending"

    def _request_approval(self, workflow):
        self.ensure_one()
        req = self.approval_request_id
        if not req or req.state in ("rejected", "cancelled"):
            req = self.env["approval.request"].create_for_record(
                self, workflow=workflow)
            self.approval_request_id = req
        return req

    def action_review(self):
        to_review = self.env["fsm.work.order"]
        need_approval = self.env["fsm.work.order"]
        for wo in self:
            if wo.state != "completed":
                raise UserError("Only completed work orders can be reviewed.")
            workflow = wo._approval_workflow()
            approved = (wo.approval_request_id
                        and wo.approval_request_id.state == "approved")
            if workflow and not approved:
                wo._request_approval(workflow)
                need_approval |= wo
            else:
                to_review |= wo
        if to_review:
            super(FsmWorkOrder, to_review).action_review()
        if need_approval:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Approval required"),
                    "message": _(
                        "%s work order(s) need approval (e.g. expensive parts) "
                        "before they can be reviewed/closed.") % len(need_approval),
                    "type": "warning", "sticky": False,
                },
            }
        return True

    def action_view_approval(self):
        self.ensure_one()
        if not self.approval_request_id:
            return False
        return {"type": "ir.actions.act_window", "res_model": "approval.request",
                "res_id": self.approval_request_id.id, "view_mode": "form",
                "target": "current"}
