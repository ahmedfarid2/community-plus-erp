from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    subscription_auto_post_default = fields.Boolean(
        string="Auto-post subscription invoices",
        config_parameter="subscriptions_lite.auto_post_default",
        help="New subscriptions default to auto-posting their generated invoices.")
