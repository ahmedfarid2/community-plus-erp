from odoo import models


class InventoryDeadStockReview(models.Model):
    _name = "inventory.dead.stock.review"
    _inherit = ["inventory.dead.stock.review", "inventory.sa.approval.mixin"]

    def action_done(self):
        # Only disposal completions are gated.
        to_done = self.browse()
        need = self.browse()
        for rec in self:
            workflow = (rec._approval_workflow()
                        if rec.recommended_action == "dispose" else None)
            if workflow and not rec._sa_is_approved():
                rec._request_sa_approval(workflow)
                need |= rec
            else:
                to_done |= rec
        if to_done:
            super(InventoryDeadStockReview, to_done).action_done()
        if need:
            return need._sa_block_notification(len(need), "disposal(s)")
        return True
