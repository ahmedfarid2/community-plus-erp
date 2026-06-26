from odoo import fields, models


class SubscriptionTemplate(models.Model):
    _name = "subscription.lite.template"
    _description = "Subscription Quotation Template"
    _order = "name"

    name = fields.Char(required=True)
    plan_id = fields.Many2one("subscription.lite.plan")
    note = fields.Text()
    active = fields.Boolean(default=True)
    line_ids = fields.One2many("subscription.lite.template.line", "template_id",
                               string="Lines")


class SubscriptionTemplateLine(models.Model):
    _name = "subscription.lite.template.line"
    _description = "Subscription Template Line"
    _order = "sequence, id"

    sequence = fields.Integer(default=10)
    template_id = fields.Many2one("subscription.lite.template", ondelete="cascade",
                                  required=True)
    product_id = fields.Many2one("product.product")
    name = fields.Char(required=True)
    quantity = fields.Float(default=1.0)
    price_unit = fields.Float()
