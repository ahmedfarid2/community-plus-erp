from odoo import _, api, fields, models


class InventorySaApprovalMixin(models.AbstractModel):
    _name = "inventory.sa.approval.mixin"
    _description = "Inventory Smart-Approval Mixin"

    sa_approval_request_id = fields.Many2one(
        "approval.request", string="Approval Request", copy=False, readonly=True)
    sa_approval_state = fields.Selection(
        [("none", "No Approval Needed"),
         ("to_request", "To Request"),
         ("pending", "Pending Approval"),
         ("approved", "Approved"),
         ("rejected", "Rejected")],
        string="Approval", compute="_compute_sa_approval_state")

    def _approval_workflow(self):
        self.ensure_one()
        workflows = self.env["approval.workflow"].sudo().search(
            [("model_name", "=", self._name), ("active", "=", True)])
        return workflows.filtered(lambda w: w._matches(self))[:1]

    @api.depends("sa_approval_request_id", "sa_approval_request_id.state")
    def _compute_sa_approval_state(self):
        for rec in self:
            req = rec.sa_approval_request_id
            if not rec._approval_workflow():
                rec.sa_approval_state = "none"
            elif not req or req.state == "cancelled":
                rec.sa_approval_state = "to_request"
            elif req.state == "approved":
                rec.sa_approval_state = "approved"
            elif req.state == "rejected":
                rec.sa_approval_state = "rejected"
            else:
                rec.sa_approval_state = "pending"

    def _request_sa_approval(self, workflow):
        self.ensure_one()
        req = self.sa_approval_request_id
        if not req or req.state in ("rejected", "cancelled"):
            req = self.env["approval.request"].create_for_record(
                self, workflow=workflow)
            self.sa_approval_request_id = req
        return req

    def _sa_is_approved(self):
        self.ensure_one()
        return (self.sa_approval_request_id
                and self.sa_approval_request_id.state == "approved")

    def _sa_block_notification(self, count, what):
        return {
            "type": "ir.actions.client", "tag": "display_notification",
            "params": {
                "title": _("Approval required"),
                "message": _("%s %s need approval first.") % (count, what),
                "type": "warning", "sticky": False,
            },
        }

    def action_view_sa_approval(self):
        self.ensure_one()
        if not self.sa_approval_request_id:
            return False
        return {"type": "ir.actions.act_window", "res_model": "approval.request",
                "res_id": self.sa_approval_request_id.id, "view_mode": "form",
                "target": "current"}
