from odoo import _, api, fields, models

VENDOR_TYPES = ("in_invoice", "in_refund")


class AccountMove(models.Model):
    _inherit = "account.move"

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
        """Active workflow that applies to this vendor bill, if any."""
        self.ensure_one()
        if self.move_type not in VENDOR_TYPES:
            return self.env["approval.workflow"]
        workflows = self.env["approval.workflow"].sudo().search(
            [("model_name", "=", "account.move"), ("active", "=", True)])
        return workflows.filtered(lambda w: w._matches(self))[:1]

    @api.depends("approval_request_id", "approval_request_id.state",
                 "amount_total", "move_type")
    def _compute_approval_state(self):
        for move in self:
            req = move.approval_request_id
            if move.move_type not in VENDOR_TYPES or not move._approval_workflow():
                move.approval_state = "none"
            elif not req or req.state == "cancelled":
                move.approval_state = "to_request"
            elif req.state == "approved":
                move.approval_state = "approved"
            elif req.state == "rejected":
                move.approval_state = "rejected"
            else:
                move.approval_state = "pending"

    def _request_approval(self, workflow):
        self.ensure_one()
        req = self.approval_request_id
        if not req or req.state in ("rejected", "cancelled"):
            req = self.env["approval.request"].create_for_record(
                self, workflow=workflow)
            self.approval_request_id = req
        return req

    def action_post(self):
        allowed = self.env["account.move"]
        need_approval = self.env["account.move"]
        for move in self:
            workflow = move._approval_workflow()
            approved = (move.approval_request_id
                        and move.approval_request_id.state == "approved")
            if not workflow or approved:
                allowed |= move
            else:
                move._request_approval(workflow)
                need_approval |= move
        res = True
        if allowed:
            res = super(AccountMove, allowed).action_post()
        if need_approval:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Approval required"),
                    "message": _(
                        "%s vendor bill(s) were submitted for approval and "
                        "cannot be posted until approved.") % len(need_approval),
                    "type": "warning",
                    "sticky": False,
                },
            }
        return res

    def action_view_approval_request(self):
        self.ensure_one()
        if not self.approval_request_id:
            return False
        return {
            "type": "ir.actions.act_window",
            "res_model": "approval.request",
            "res_id": self.approval_request_id.id,
            "view_mode": "form",
            "target": "current",
        }
