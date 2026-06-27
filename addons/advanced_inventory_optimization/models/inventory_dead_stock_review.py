from odoo import api, fields, models


class InventoryDeadStockReview(models.Model):
    _name = "inventory.dead.stock.review"
    _description = "Dead Stock Review"
    _inherit = ["mail.thread", "mail.activity.mixin", "inventory.log.mixin"]
    _order = "create_date desc, id desc"

    name = fields.Char(required=True, copy=False, readonly=True,
                       default=lambda s: "New")
    product_id = fields.Many2one("product.product", required=True, index=True)
    warehouse_id = fields.Many2one("stock.warehouse", index=True)
    company_id = fields.Many2one("res.company", default=lambda s: s.env.company)
    currency_id = fields.Many2one(
        "res.currency", default=lambda s: s.env.company.currency_id)
    qty_on_hand = fields.Float()
    stock_value = fields.Monetary(currency_field="currency_id")
    last_movement_date = fields.Date()
    days_without_movement = fields.Integer()
    recommended_action = fields.Selection(
        [("discount", "Discount"), ("return_to_vendor", "Return to Vendor"),
         ("transfer", "Transfer"), ("bundle", "Bundle"), ("dispose", "Dispose"),
         ("keep", "Keep"), ("investigate", "Investigate")],
        default="investigate")
    responsible_user_id = fields.Many2one("res.users",
                                          default=lambda s: s.env.user)
    state = fields.Selection(
        [("draft", "Draft"), ("under_review", "Under Review"),
         ("action_planned", "Action Planned"), ("done", "Done"),
         ("cancelled", "Cancelled")], default="draft", required=True,
        tracking=True)
    action_notes = fields.Text()
    notes = fields.Text()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "inventory.dead.stock.review") or "New"
        reviews = super().create(vals_list)
        reviews._log("dead_stock_review_created")
        return reviews

    def action_start_review(self):
        self.write({"state": "under_review"})

    def action_plan_action(self):
        self.write({"state": "action_planned"})

    def action_done(self):
        self.write({"state": "done"})

    def action_cancel(self):
        self.write({"state": "cancelled"})

    def action_reset_to_draft(self):
        self.write({"state": "draft"})
