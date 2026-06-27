from odoo import _, api, fields, models


class ProcurementAward(models.Model):
    _inherit = "procurement.award"

    # Stored vendor risk so workflows can target high-risk awards by domain.
    vendor_risk_level = fields.Selection(
        [("low", "Low"), ("medium", "Medium"), ("high", "High"),
         ("blocked", "Blocked")], compute="_compute_vendor_risk", store=True)

    sa_approval_request_id = fields.Many2one(
        "approval.request", string="Workflow Approval", copy=False, readonly=True)
    sa_approval_state = fields.Selection(
        [("none", "No Approval Needed"),
         ("to_request", "To Request"),
         ("pending", "Pending Approval"),
         ("approved", "Approved"),
         ("rejected", "Rejected")],
        string="Award Approval", compute="_compute_sa_approval_state")

    @api.depends("vendor_id")
    def _compute_vendor_risk(self):
        Profile = self.env["procurement.vendor.profile"]
        for aw in self:
            prof = Profile.search([("partner_id", "=", aw.vendor_id.id)], limit=1)
            aw.vendor_risk_level = prof.risk_level if prof else "low"

    def _approval_workflow(self):
        self.ensure_one()
        workflows = self.env["approval.workflow"].sudo().search(
            [("model_name", "=", "procurement.award"), ("active", "=", True)])
        return workflows.filtered(lambda w: w._matches(self))[:1]

    @api.depends("sa_approval_request_id", "sa_approval_request_id.state",
                 "total_awarded_amount", "vendor_risk_level", "state")
    def _compute_sa_approval_state(self):
        for aw in self:
            req = aw.sa_approval_request_id
            if not aw._approval_workflow():
                aw.sa_approval_state = "none"
            elif not req or req.state == "cancelled":
                aw.sa_approval_state = "to_request"
            elif req.state == "approved":
                aw.sa_approval_state = "approved"
            elif req.state == "rejected":
                aw.sa_approval_state = "rejected"
            else:
                aw.sa_approval_state = "pending"

    def _request_sa_approval(self, workflow):
        self.ensure_one()
        req = self.sa_approval_request_id
        if not req or req.state in ("rejected", "cancelled"):
            req = self.env["approval.request"].create_for_record(
                self, workflow=workflow)
            self.sa_approval_request_id = req
        return req

    def action_approve(self):
        to_approve = self.env["procurement.award"]
        need_approval = self.env["procurement.award"]
        for aw in self:
            workflow = aw._approval_workflow()
            approved = (aw.sa_approval_request_id
                        and aw.sa_approval_request_id.state == "approved")
            if workflow and not approved:
                aw._request_sa_approval(workflow)
                if aw.state == "draft":
                    aw.write({"state": "pending_approval",
                              "approval_state": "pending"})
                need_approval |= aw
            else:
                to_approve |= aw
        if to_approve:
            super(ProcurementAward, to_approve).action_approve()
        if need_approval:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Approval required"),
                    "message": _(
                        "%s award(s) need workflow approval (high value / risky "
                        "vendor) before they can be approved.") % len(need_approval),
                    "type": "warning", "sticky": False,
                },
            }
        return True

    def action_view_sa_approval(self):
        self.ensure_one()
        if not self.sa_approval_request_id:
            return False
        return {"type": "ir.actions.act_window", "res_model": "approval.request",
                "res_id": self.sa_approval_request_id.id, "view_mode": "form",
                "target": "current"}
