from odoo import fields, models


class SubscriptionCancelWizard(models.TransientModel):
    _name = "subscription.cancel.wizard"
    _description = "Cancel Subscription Wizard"

    subscription_id = fields.Many2one(
        "subscription.subscription", required=True)
    reason_id = fields.Many2one(
        "subscription.cancellation.reason", string="Cancellation Reason",
        required=True)
    note = fields.Text(string="Note")

    def action_confirm(self):
        self.ensure_one()
        self.subscription_id._set_cancelled(self.reason_id, self.note)
        return {"type": "ir.actions.act_window_close"}
