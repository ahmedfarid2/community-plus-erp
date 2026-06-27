from odoo import _, api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    discount_total = fields.Monetary(
        string="Total Discount", compute="_compute_discount_total", store=True,
        currency_field="currency_id",
        help="Total amount discounted across the order lines. Used by "
             "amount-based approval workflows.")

    approval_request_id = fields.Many2one(
        "approval.request", string="Approval Request", copy=False, readonly=True)
    approval_state = fields.Selection(
        [("none", "No Approval Needed"),
         ("to_request", "To Request"),
         ("pending", "Pending Approval"),
         ("approved", "Approved"),
         ("rejected", "Rejected")],
        string="Approval", compute="_compute_approval_state")

    @api.depends("order_line.price_unit", "order_line.product_uom_qty",
                 "order_line.discount")
    def _compute_discount_total(self):
        for order in self:
            total = 0.0
            for line in order.order_line:
                total += (line.price_unit * line.product_uom_qty
                          * (line.discount or 0.0) / 100.0)
            order.discount_total = total

    def _approval_workflow(self):
        self.ensure_one()
        workflows = self.env["approval.workflow"].sudo().search(
            [("model_name", "=", "sale.order"), ("active", "=", True)])
        return workflows.filtered(lambda w: w._matches(self))[:1]

    @api.depends("approval_request_id", "approval_request_id.state",
                 "discount_total")
    def _compute_approval_state(self):
        for order in self:
            req = order.approval_request_id
            if not order._approval_workflow():
                order.approval_state = "none"
            elif not req or req.state == "cancelled":
                order.approval_state = "to_request"
            elif req.state == "approved":
                order.approval_state = "approved"
            elif req.state == "rejected":
                order.approval_state = "rejected"
            else:
                order.approval_state = "pending"

    def _request_approval(self, workflow):
        self.ensure_one()
        req = self.approval_request_id
        if not req or req.state in ("rejected", "cancelled"):
            req = self.env["approval.request"].create_for_record(
                self, workflow=workflow)
            self.approval_request_id = req
        return req

    def action_confirm(self):
        to_confirm = self.env["sale.order"]
        need_approval = self.env["sale.order"]
        for order in self:
            workflow = order._approval_workflow()
            approved = (order.approval_request_id
                        and order.approval_request_id.state == "approved")
            if not workflow or approved:
                to_confirm |= order
            else:
                order._request_approval(workflow)
                need_approval |= order
        res = True
        if to_confirm:
            res = super(SaleOrder, to_confirm).action_confirm()
        if need_approval:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Approval required"),
                    "message": _(
                        "%s sales order(s) were submitted for approval and "
                        "cannot be confirmed until approved.") % len(need_approval),
                    "type": "warning",
                    "sticky": False,
                },
            }
        return res

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
