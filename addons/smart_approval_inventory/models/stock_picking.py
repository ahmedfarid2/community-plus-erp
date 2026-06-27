from odoo import _, api, fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

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
            [("model_name", "=", "stock.picking"), ("active", "=", True)])
        return workflows.filtered(lambda w: w._matches(self))[:1]

    @api.depends("approval_request_id", "approval_request_id.state", "state")
    def _compute_approval_state(self):
        for picking in self:
            req = picking.approval_request_id
            if not picking._approval_workflow():
                picking.approval_state = "none"
            elif not req or req.state == "cancelled":
                picking.approval_state = "to_request"
            elif req.state == "approved":
                picking.approval_state = "approved"
            elif req.state == "rejected":
                picking.approval_state = "rejected"
            else:
                picking.approval_state = "pending"

    def _request_approval(self, workflow):
        self.ensure_one()
        req = self.approval_request_id
        if not req or req.state in ("rejected", "cancelled"):
            req = self.env["approval.request"].create_for_record(
                self, workflow=workflow)
            self.approval_request_id = req
        return req

    def button_validate(self):
        need_approval = self.env["stock.picking"]
        for picking in self:
            workflow = picking._approval_workflow()
            approved = (picking.approval_request_id
                        and picking.approval_request_id.state == "approved")
            if workflow and not approved:
                picking._request_approval(workflow)
                need_approval |= picking
        if need_approval:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Approval required"),
                    "message": _(
                        "%s transfer(s) were submitted for approval and cannot "
                        "be validated until approved.") % len(need_approval),
                    "type": "warning",
                    "sticky": False,
                },
            }
        return super().button_validate()

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
