from odoo import fields, models


class CpqPricingRule(models.Model):
    _name = "cpq.pricing.rule"
    _description = "CPQ Pricing Rule"
    _order = "sequence, id"

    template_id = fields.Many2one(
        "cpq.template", string="Template", required=True, ondelete="cascade",
        index=True)
    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(
        default=10, help="Rules are applied in ascending sequence order.")
    active = fields.Boolean(default=True)

    condition_type = fields.Selection(
        [("always", "Always"),
         ("option_selected", "When option selected"),
         ("quantity_based", "Quantity based"),
         ("amount_based", "Amount based"),
         ("domain_based", "Domain based"),
         ("formula_based", "Formula based")],
        string="Condition", default="always", required=True)
    condition_expression = fields.Char(
        string="Condition Expression",
        help="Safe boolean expression. Variables: quantity, current_total, "
             "base_price, area, selected_options_count, and selected_codes "
             "(set of selected option codes). "
             "E.g. \"'PREMIUM' in selected_codes\" or \"quantity > 10\".")

    price_action = fields.Selection(
        [("add_fixed", "Add fixed amount"),
         ("add_percentage", "Add percentage"),
         ("set_price", "Set price"),
         ("discount_fixed", "Discount fixed amount"),
         ("discount_percentage", "Discount percentage"),
         ("formula", "Formula")],
        string="Action", default="add_fixed", required=True)
    amount = fields.Float()
    percentage = fields.Float(string="Percentage (%)")
    formula_expression = fields.Char(
        string="Action Formula",
        help="Safe expression returning the new total. Variables include "
             "current_total, base_price, quantity, area.")
    applies_to = fields.Selection(
        [("total", "Total")],
        string="Applies To", default="total", required=True,
        help="MVP applies rules to the configuration total. Option/group "
             "scopes are reserved for a future version.")
    notes = fields.Text()
