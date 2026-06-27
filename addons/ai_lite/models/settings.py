from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    ai_provider = fields.Selection(
        [("ollama", "Ollama (local, free)"), ("openai", "OpenAI"),
         ("anthropic", "Anthropic")],
        string="AI Provider", default="ollama",
        config_parameter="ai_lite.provider")
    ai_model = fields.Char(string="Model", config_parameter="ai_lite.model")
    ai_api_key = fields.Char(string="API Key", config_parameter="ai_lite.api_key")
    ai_base_url = fields.Char(string="Base URL (optional)",
                              config_parameter="ai_lite.base_url")
