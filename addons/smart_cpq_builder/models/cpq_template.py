from odoo import api, fields, models


class CpqTemplate(models.Model):
    _name = "cpq.template"
    _description = "CPQ Configuration Template"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name"

    name = fields.Char(required=True, translate=True, tracking=True)
    code = fields.Char(help="Short technical code, useful for imports.")
    active = fields.Boolean(default=True)
    state = fields.Selection(
        [("draft", "Draft"), ("active", "Active"), ("archived", "Archived")],
        default="draft", required=True, tracking=True)
    company_id = fields.Many2one(
        "res.company", default=lambda s: s.env.company)
    currency_id = fields.Many2one(
        "res.currency", required=True,
        default=lambda s: s.env.company.currency_id)
    base_product_id = fields.Many2one(
        "product.product", string="Base Product",
        help="Optional product this configuration is based on. Its cost is "
             "used in margin calculations when set.")
    category_id = fields.Many2one(
        "product.category", string="Category")
    base_price = fields.Monetary(
        currency_field="currency_id",
        help="Starting price before options and pricing rules.")
    description = fields.Html(string="Customer Description")
    notes = fields.Text(string="Internal Notes")

    option_group_ids = fields.One2many(
        "cpq.option.group", "template_id", string="Option Groups", copy=True)
    pricing_rule_ids = fields.One2many(
        "cpq.pricing.rule", "template_id", string="Pricing Rules", copy=True)
    compatibility_rule_ids = fields.One2many(
        "cpq.compatibility.rule", "template_id", string="Compatibility Rules",
        copy=True)

    option_count = fields.Integer(compute="_compute_counts")
    configuration_count = fields.Integer(compute="_compute_counts")

    @api.depends("option_group_ids.option_ids")
    def _compute_counts(self):
        config_data = {}
        if self.ids:
            groups = self.env["cpq.configuration"]._read_group(
                [("template_id", "in", self.ids)], ["template_id"], ["__count"])
            config_data = {t.id: c for t, c in groups}
        for tmpl in self:
            tmpl.option_count = sum(
                len(g.option_ids) for g in tmpl.option_group_ids)
            tmpl.configuration_count = config_data.get(tmpl.id, 0)

    # --- state transitions ---
    def action_activate(self):
        self.write({"state": "active", "active": True})

    def action_archive_template(self):
        self.write({"state": "archived", "active": False})

    def action_reset_to_draft(self):
        self.write({"state": "draft", "active": True})

    def action_duplicate_template(self):
        self.ensure_one()
        copy = self.copy({"name": "%s (copy)" % self.name, "state": "draft"})
        return {
            "type": "ir.actions.act_window",
            "res_model": "cpq.template",
            "res_id": copy.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_view_configurations(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Configurations",
            "res_model": "cpq.configuration",
            "view_mode": "list,form",
            "domain": [("template_id", "=", self.id)],
            "context": {"default_template_id": self.id},
        }
