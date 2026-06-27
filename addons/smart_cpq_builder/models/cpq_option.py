from odoo import api, fields, models
from odoo.exceptions import ValidationError


class CpqOption(models.Model):
    _name = "cpq.option"
    _description = "CPQ Option"
    _order = "sequence, id"

    group_id = fields.Many2one(
        "cpq.option.group", string="Option Group", required=True,
        ondelete="cascade", index=True)
    template_id = fields.Many2one(
        related="group_id.template_id", store=True, string="Template",
        index=True)
    currency_id = fields.Many2one(
        related="template_id.currency_id", string="Currency")
    name = fields.Char(required=True, translate=True)
    code = fields.Char()
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    price_type = fields.Selection(
        [("none", "No price"),
         ("fixed", "Fixed amount"),
         ("percentage", "% of base price"),
         ("formula", "Formula")],
        string="Price Type", default="fixed", required=True)
    fixed_price = fields.Monetary(currency_field="currency_id")
    percentage_value = fields.Float(string="Percentage (%)")
    formula_expression = fields.Char(
        string="Formula",
        help="Safe expression using variables: base_price, quantity, width, "
             "height, length, area, selected_options_count. No raw eval.")
    cost = fields.Monetary(
        currency_field="currency_id",
        help="Unit cost of this option, used for margin calculations.")
    margin_percent = fields.Float(
        string="Target Margin (%)",
        help="Optional reference margin for this option.")
    description = fields.Text()
    help_text = fields.Char(string="Help Text")
    image = fields.Image(string="Image", max_width=512, max_height=512)

    @api.constrains("price_type", "formula_expression")
    def _check_formula(self):
        for opt in self:
            if opt.price_type == "formula" and not opt.formula_expression:
                raise ValidationError(
                    "Option '%s' uses a formula price but has no formula."
                    % opt.name)
