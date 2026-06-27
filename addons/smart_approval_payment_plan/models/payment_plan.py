from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PaymentPlan(models.Model):
    _inherit = "payment.plan"

    discount_amount = fields.Monetary(
        string="Requested Discount / Waiver", currency_field="currency_id",
        help="Amount to discount or write off from this plan's remaining "
             "balance. Routed through approval when it meets a configured "
             "amount-based workflow.")
    discount_reason = fields.Char(string="Discount Reason")
    discount_applied = fields.Monetary(
        string="Discount Applied", currency_field="currency_id", readonly=True,
        copy=False, help="Cumulative discount/waiver already applied.")

    approval_request_id = fields.Many2one(
        "approval.request", string="Approval Request", copy=False, readonly=True)
    approval_state = fields.Selection(
        [("none", "No Approval Needed"),
         ("to_request", "To Request"),
         ("pending", "Pending Approval"),
         ("approved", "Approved"),
         ("rejected", "Rejected")],
        string="Discount Approval", compute="_compute_approval_state")

    def _discount_workflow(self):
        """Active workflow that applies to this plan (typically amount-based on
        the requested discount)."""
        self.ensure_one()
        workflows = self.env["approval.workflow"].sudo().search(
            [("model_name", "=", "payment.plan"), ("active", "=", True)])
        return workflows.filtered(lambda w: w._matches(self))[:1]

    @api.depends("approval_request_id", "approval_request_id.state",
                 "discount_amount")
    def _compute_approval_state(self):
        for plan in self:
            req = plan.approval_request_id
            if not req and not plan._discount_workflow():
                plan.approval_state = "none"
            elif not req or req.state == "cancelled":
                plan.approval_state = "to_request"
            elif req.state == "approved":
                plan.approval_state = "approved"
            elif req.state == "rejected":
                plan.approval_state = "rejected"
            else:
                plan.approval_state = "pending"

    def _request_discount_approval(self, workflow):
        self.ensure_one()
        req = self.approval_request_id
        if not req or req.state in ("rejected", "cancelled"):
            req = self.env["approval.request"].create_for_record(
                self, workflow=workflow)
            self.approval_request_id = req
        return req

    def _apply_discount(self):
        """Reduce the unpaid lines (latest first) by the requested discount."""
        self.ensure_one()
        remaining = self.discount_amount
        for line in self.line_ids.sorted(
                key=lambda l: l.due_date or fields.Date.today(), reverse=True):
            if remaining <= 0:
                break
            if line.remaining_amount <= 0:
                continue
            cut = min(line.remaining_amount, remaining)
            line.amount = line.amount - cut
            remaining -= cut
        applied = self.discount_amount - remaining
        self.discount_applied += applied
        self.message_post(body=_(
            "Discount / waiver of %(amount)s applied. %(reason)s",
            amount=applied, reason=self.discount_reason or ""))
        self.write({"discount_amount": 0.0, "discount_reason": False,
                    "approval_request_id": False})

    def action_apply_discount(self):
        self.ensure_one()
        if self.discount_amount <= 0:
            raise UserError(_("Enter a positive discount/waiver amount first."))
        if self.discount_amount > self.remaining_amount:
            raise UserError(_(
                "The discount cannot exceed the remaining amount (%s).")
                % self.remaining_amount)
        workflow = self._discount_workflow()
        approved = (self.approval_request_id
                    and self.approval_request_id.state == "approved")
        if workflow and not approved:
            req = self._request_discount_approval(workflow)
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Approval required"),
                    "message": _(
                        "This discount needs approval. Request %s was "
                        "submitted.") % req.name,
                    "type": "warning",
                    "sticky": False,
                },
            }
        self._apply_discount()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {"title": _("Discount applied"),
                       "message": _("The discount/waiver was applied to the plan."),
                       "type": "success", "sticky": False},
        }

    def action_view_discount_approval(self):
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
