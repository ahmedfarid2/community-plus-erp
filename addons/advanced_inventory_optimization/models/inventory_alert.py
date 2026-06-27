from odoo import fields, models


class InventoryAlert(models.Model):
    _name = "inventory.alert"
    _description = "Inventory Alert"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "detected_date desc, id desc"

    name = fields.Char(required=True, default="Alert")
    alert_type = fields.Selection(
        [("stockout_risk", "Stockout Risk"), ("overstock", "Overstock"),
         ("slow_moving", "Slow Moving"), ("dead_stock", "Dead Stock"),
         ("negative_stock", "Negative Stock"),
         ("abnormal_movement", "Abnormal Movement"),
         ("low_coverage", "Low Coverage"), ("high_coverage", "High Coverage")],
        string="Type", required=True, index=True)
    product_id = fields.Many2one("product.product", required=True, index=True)
    warehouse_id = fields.Many2one("stock.warehouse", index=True)
    company_id = fields.Many2one("res.company", default=lambda s: s.env.company)
    severity = fields.Selection(
        [("info", "Info"), ("warning", "Warning"), ("critical", "Critical")],
        default="warning", required=True, index=True)
    message = fields.Char()
    detected_date = fields.Datetime(default=fields.Datetime.now)
    responsible_user_id = fields.Many2one("res.users")
    state = fields.Selection(
        [("open", "Open"), ("acknowledged", "Acknowledged"),
         ("resolved", "Resolved"), ("ignored", "Ignored")],
        default="open", required=True, tracking=True, index=True)
    resolved_date = fields.Datetime(readonly=True)
    notes = fields.Text()

    def action_acknowledge(self):
        self.write({"state": "acknowledged"})

    def action_resolve(self):
        self.write({"state": "resolved",
                    "resolved_date": fields.Datetime.now()})

    def action_ignore(self):
        self.write({"state": "ignored"})

    def action_create_activity(self):
        for a in self:
            a.activity_schedule(
                "mail.mail_activity_data_todo",
                user_id=a.responsible_user_id.id or a.env.uid,
                summary="%s: %s" % (dict(a._fields["alert_type"].selection).get(
                    a.alert_type), a.product_id.display_name),
                note=a.message or "")

    def action_view_product(self):
        self.ensure_one()
        return {"type": "ir.actions.act_window", "res_model": "product.product",
                "res_id": self.product_id.id, "view_mode": "form"}
