from odoo import _, api, fields, models
from odoo.exceptions import UserError


class CpqConfiguration(models.Model):
    _inherit = "cpq.configuration"

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
            [("model_name", "=", "cpq.configuration"), ("active", "=", True)])
        return workflows.filtered(lambda w: w._matches(self))[:1]

    @api.depends("approval_request_id", "approval_request_id.state",
                 "margin_percent", "discount_amount", "total_price")
    def _compute_approval_state(self):
        for cfg in self:
            req = cfg.approval_request_id
            if not cfg._approval_workflow():
                cfg.approval_state = "none"
            elif not req or req.state == "cancelled":
                cfg.approval_state = "to_request"
            elif req.state == "approved":
                cfg.approval_state = "approved"
            elif req.state == "rejected":
                cfg.approval_state = "rejected"
            else:
                cfg.approval_state = "pending"

    def _request_approval(self, workflow):
        self.ensure_one()
        req = self.approval_request_id
        if not req or req.state in ("rejected", "cancelled"):
            req = self.env["approval.request"].create_for_record(
                self, workflow=workflow)
            self.approval_request_id = req
        return req

    def action_validate(self):
        to_validate = self.env["cpq.configuration"]
        need_approval = self.env["cpq.configuration"]
        for cfg in self:
            # Run the engine's own validation (compat/required) first.
            cfg._recalculate()
            errors, _warnings = cfg._validation_issues()
            if errors:
                raise UserError(
                    "Configuration is not valid:\n• " + "\n• ".join(errors))
            workflow = cfg._approval_workflow()
            approved = (cfg.approval_request_id
                        and cfg.approval_request_id.state == "approved")
            if workflow and not approved:
                cfg._request_approval(workflow)
                need_approval |= cfg
            else:
                to_validate |= cfg
        if to_validate:
            super(CpqConfiguration, to_validate).action_validate()
        if need_approval:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Approval required"),
                    "message": _(
                        "%s configuration(s) were submitted for approval "
                        "(e.g. low margin) and cannot be validated yet.")
                    % len(need_approval),
                    "type": "warning",
                    "sticky": False,
                },
            }
        return True

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
