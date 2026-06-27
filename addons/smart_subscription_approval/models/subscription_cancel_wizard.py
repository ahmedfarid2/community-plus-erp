from odoo import _, models


class SubscriptionCancelWizard(models.TransientModel):
    _inherit = "subscription.cancel.wizard"

    def action_confirm(self):
        self.ensure_one()
        sub = self.subscription_id
        workflow = sub._cancellation_workflow()
        approved = (sub.approval_request_id
                    and sub.approval_request_id.state == "approved")
        if workflow and not approved:
            sub._request_cancel_approval(workflow)
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Approval required"),
                    "message": _(
                        "Cancelling this subscription needs approval (%s was "
                        "submitted). Re-confirm the cancellation once approved.")
                    % sub.approval_request_id.name,
                    "type": "warning", "sticky": False,
                },
            }
        return super().action_confirm()
