from odoo import api, fields, models
from odoo.exceptions import UserError


class SubscriptionChangeWizard(models.TransientModel):
    _name = "subscription.change.wizard"
    _description = "Change Plan Wizard"

    subscription_id = fields.Many2one(
        "subscription.subscription", required=True)
    new_plan_id = fields.Many2one(
        "subscription.plan", string="New Plan", required=True,
        domain="[('state','=','active')]")
    new_price = fields.Monetary(currency_field="currency_id")
    currency_id = fields.Many2one(related="subscription_id.currency_id")
    effective_date = fields.Date(default=fields.Date.context_today, required=True)
    proration_policy = fields.Selection(
        [("none", "None"), ("immediate", "Immediate"),
         ("next_cycle", "Next Cycle")],
        default="none", required=True)
    reason = fields.Char()

    @api.onchange("new_plan_id")
    def _onchange_new_plan(self):
        if self.new_plan_id:
            self.new_price = self.new_plan_id.price

    def action_confirm(self):
        self.ensure_one()
        sub = self.subscription_id
        if self.new_plan_id == sub.plan_id and self.new_price == sub.recurring_price:
            raise UserError("Pick a different plan or price.")
        old_plan, old_price = sub.plan_id, sub.recurring_price
        change_type = ("upgrade" if self.new_price > old_price
                       else "downgrade" if self.new_price < old_price
                       else "plan_change")
        self.env["subscription.change"].create({
            "subscription_id": sub.id,
            "change_type": change_type,
            "old_plan_id": old_plan.id, "new_plan_id": self.new_plan_id.id,
            "old_price": old_price, "new_price": self.new_price,
            "effective_date": self.effective_date,
            "proration_policy": self.proration_policy,
            "state": "applied", "reason": self.reason,
        })
        sub.write({"plan_id": self.new_plan_id.id,
                   "recurring_price": self.new_price})
        sub._log_event(
            "upgraded" if change_type == "upgrade"
            else "downgraded" if change_type == "downgrade" else "price_changed",
            old_plan=old_plan, new_plan=self.new_plan_id,
            old_amount=old_price, new_amount=self.new_price,
            reason=self.reason)
        return {"type": "ir.actions.act_window_close"}
