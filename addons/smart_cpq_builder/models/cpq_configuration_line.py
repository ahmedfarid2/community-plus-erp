from odoo import fields, models


class CpqConfigurationLine(models.Model):
    _name = "cpq.configuration.line"
    _description = "CPQ Configuration Line"
    _order = "id"

    configuration_id = fields.Many2one(
        "cpq.configuration", string="Configuration", required=True,
        ondelete="cascade", index=True)
    currency_id = fields.Many2one(
        related="configuration_id.currency_id", string="Currency")
    group_id = fields.Many2one("cpq.option.group", string="Group")
    option_id = fields.Many2one("cpq.option", string="Option")
    quantity = fields.Float(default=1.0)
    unit_price = fields.Monetary(currency_field="currency_id")
    subtotal = fields.Monetary(currency_field="currency_id")
    notes = fields.Char()
