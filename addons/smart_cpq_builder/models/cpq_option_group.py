from odoo import api, fields, models
from odoo.exceptions import ValidationError


class CpqOptionGroup(models.Model):
    _name = "cpq.option.group"
    _description = "CPQ Option Group"
    _order = "sequence, id"

    template_id = fields.Many2one(
        "cpq.template", string="Template", required=True, ondelete="cascade",
        index=True)
    name = fields.Char(required=True, translate=True)
    code = fields.Char()
    sequence = fields.Integer(default=10)
    selection_type = fields.Selection(
        [("single", "Single choice"), ("multiple", "Multiple choice")],
        default="single", required=True,
        help="Single: at most one option. Multiple: respects min/max selection.")
    is_required = fields.Boolean(
        string="Required",
        help="A valid selection in this group is mandatory to validate a "
             "configuration.")
    min_selection = fields.Integer(string="Min Selection", default=0)
    max_selection = fields.Integer(
        string="Max Selection", default=0,
        help="0 means no upper limit (multiple-choice groups).")
    help_text = fields.Char(string="Help Text")
    active = fields.Boolean(default=True)
    option_ids = fields.One2many(
        "cpq.option", "group_id", string="Options", copy=True)

    @api.constrains("min_selection", "max_selection", "selection_type")
    def _check_selection_bounds(self):
        for group in self:
            if group.min_selection < 0 or group.max_selection < 0:
                raise ValidationError(
                    "Selection bounds cannot be negative on '%s'." % group.name)
            if (group.max_selection and group.min_selection
                    and group.min_selection > group.max_selection):
                raise ValidationError(
                    "Min Selection cannot exceed Max Selection on '%s'."
                    % group.name)
