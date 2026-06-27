from odoo import api, fields, models


class Subscription(models.Model):
    _inherit = "subscription.subscription"

    approval_request_id = fields.Many2one(
        "approval.request", string="Approval Request", copy=False, readonly=True)
    approval_state = fields.Selection(
        [("none", "No Approval Needed"),
         ("to_request", "To Request"),
         ("pending", "Pending Approval"),
         ("approved", "Approved"),
         ("rejected", "Rejected")],
        string="Cancellation Approval", compute="_compute_approval_state")

    def _cancellation_workflow(self):
        """Active approval workflow that applies to this subscription, if any."""
        self.ensure_one()
        workflows = self.env["approval.workflow"].sudo().search(
            [("model_name", "=", "subscription.subscription"),
             ("active", "=", True)])
        return workflows.filtered(lambda w: w._matches(self))[:1]

    @api.depends("approval_request_id", "approval_request_id.state",
                 "mrr_amount", "state")
    def _compute_approval_state(self):
        for sub in self:
            req = sub.approval_request_id
            if not sub._cancellation_workflow():
                sub.approval_state = "none"
            elif not req or req.state == "cancelled":
                sub.approval_state = "to_request"
            elif req.state == "approved":
                sub.approval_state = "approved"
            elif req.state == "rejected":
                sub.approval_state = "rejected"
            else:
                sub.approval_state = "pending"

    def _request_cancel_approval(self, workflow):
        self.ensure_one()
        req = self.approval_request_id
        if not req or req.state in ("rejected", "cancelled"):
            req = self.env["approval.request"].create_for_record(
                self, workflow=workflow)
            self.approval_request_id = req
        return req

    def action_view_cancel_approval(self):
        self.ensure_one()
        if not self.approval_request_id:
            return False
        return {
            "type": "ir.actions.act_window",
            "res_model": "approval.request",
            "res_id": self.approval_request_id.id,
            "view_mode": "form", "target": "current",
        }
