from odoo import fields, models


class FsmAssetType(models.Model):
    _name = "fsm.asset.type"
    _description = "Asset Type"
    _order = "name"

    name = fields.Char(required=True, translate=True)
    code = fields.Char()
    active = fields.Boolean(default=True)
    description = fields.Text()
