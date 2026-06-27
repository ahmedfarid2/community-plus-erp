from odoo import fields, models


class CpqCalculationLog(models.Model):
    _name = "cpq.calculation.log"
    _description = "CPQ Calculation Log"
    _order = "id"

    configuration_id = fields.Many2one(
        "cpq.configuration", string="Configuration", required=True,
        ondelete="cascade", index=True)
    currency_id = fields.Many2one(
        related="configuration_id.currency_id", string="Currency")
    rule_id = fields.Many2one("cpq.pricing.rule", string="Rule")
    description = fields.Char()
    amount_before = fields.Monetary(currency_field="currency_id")
    amount_after = fields.Monetary(currency_field="currency_id")
    price_delta = fields.Monetary(currency_field="currency_id")
    message = fields.Char()
