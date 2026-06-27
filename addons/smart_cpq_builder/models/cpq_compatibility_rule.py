from odoo import api, fields, models
from odoo.exceptions import ValidationError


class CpqCompatibilityRule(models.Model):
    _name = "cpq.compatibility.rule"
    _description = "CPQ Compatibility Rule"
    _order = "id"

    template_id = fields.Many2one(
        "cpq.template", string="Template", required=True, ondelete="cascade",
        index=True)
    name = fields.Char(required=True, translate=True)
    active = fields.Boolean(default=True)
    rule_type = fields.Selection(
        [("requires", "Requires"),
         ("excludes", "Excludes"),
         ("warning", "Warning")],
        string="Rule Type", default="requires", required=True,
        help="Requires: if source is selected, target must be too. "
             "Excludes/Warning: source and target should not be selected "
             "together.")
    source_option_id = fields.Many2one(
        "cpq.option", string="Source Option", required=True,
        ondelete="cascade")
    target_option_id = fields.Many2one(
        "cpq.option", string="Target Option", required=True,
        ondelete="cascade")
    message = fields.Char(string="Message", translate=True)
    severity = fields.Selection(
        [("info", "Info"), ("warning", "Warning"), ("blocking", "Blocking")],
        default="blocking", required=True,
        help="Blocking prevents validation; info/warning only show a message.")

    @api.constrains("source_option_id", "target_option_id")
    def _check_options(self):
        for rule in self:
            if rule.source_option_id == rule.target_option_id:
                raise ValidationError(
                    "Source and target options must differ on '%s'." % rule.name)

    def _violated(self, selected_options):
        """Return True if this rule is violated by the selected option set."""
        self.ensure_one()
        src = self.source_option_id in selected_options
        tgt = self.target_option_id in selected_options
        if self.rule_type == "requires":
            return src and not tgt
        # excludes / warning: both selected is the conflict
        return src and tgt

    def _default_message(self):
        self.ensure_one()
        if self.message:
            return self.message
        if self.rule_type == "requires":
            return "%s requires %s." % (
                self.source_option_id.name, self.target_option_id.name)
        return "%s is not compatible with %s." % (
            self.source_option_id.name, self.target_option_id.name)
