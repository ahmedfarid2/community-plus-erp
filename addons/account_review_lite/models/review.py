from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    review_fully_delivered = fields.Boolean(
        string="Fully Delivered", compute="_compute_review_delivered", store=True)

    @api.depends("order_line.qty_delivered", "order_line.product_uom_qty",
                 "order_line.display_type", "state")
    def _compute_review_delivered(self):
        for order in self:
            lines = order.order_line.filtered(
                lambda l: not l.display_type and l.product_id)
            order.review_fully_delivered = bool(lines) and all(
                l.qty_delivered >= l.product_uom_qty for l in lines)


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    review_fully_received = fields.Boolean(
        string="Fully Received", compute="_compute_review_received", store=True)

    @api.depends("order_line.qty_received", "order_line.product_qty",
                 "order_line.display_type", "state")
    def _compute_review_received(self):
        for order in self:
            lines = order.order_line.filtered(
                lambda l: not l.display_type and l.product_id)
            order.review_fully_received = bool(lines) and all(
                l.qty_received >= l.product_qty for l in lines)
