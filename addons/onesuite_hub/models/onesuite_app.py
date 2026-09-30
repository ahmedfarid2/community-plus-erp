from odoo import fields, models


class OneSuiteApp(models.Model):
    _name = "onesuite.app"
    _description = "OneSuite Application"
    _order = "sequence, name"

    name = fields.Char(required=True)
    description = fields.Char()
    category = fields.Selection(
        [
            ("erp", "ERP & Business"),
            ("commerce", "Commerce"),
            ("operations", "Operations"),
            ("infrastructure", "Infrastructure"),
            ("service", "Services"),
        ],
        default="service",
        required=True,
    )
    url = fields.Char(required=True)
    icon = fields.Char(default="fa-th-large")
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    open_new_tab = fields.Boolean(default=True)
    status = fields.Selection(
        [
            ("active", "Active"),
            ("maintenance", "Maintenance"),
            ("planned", "Planned"),
        ],
        default="active",
        required=True,
    )

    def action_open(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": self.url,
            "target": "new" if self.open_new_tab else "self",
        }
