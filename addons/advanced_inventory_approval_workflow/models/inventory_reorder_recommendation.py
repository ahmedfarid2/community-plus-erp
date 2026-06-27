from odoo import models


class InventoryReorderRecommendation(models.Model):
    _name = "inventory.reorder.recommendation"
    _inherit = ["inventory.reorder.recommendation", "inventory.sa.approval.mixin"]

    def action_approve(self):
        to_approve = self.browse()
        need = self.browse()
        for rec in self:
            workflow = rec._approval_workflow()
            if workflow and not rec._sa_is_approved():
                rec._request_sa_approval(workflow)
                need |= rec
            else:
                to_approve |= rec
        if to_approve:
            super(InventoryReorderRecommendation, to_approve).action_approve()
        if need:
            return need._sa_block_notification(
                len(need), "high-value reorder(s)")
        return True
