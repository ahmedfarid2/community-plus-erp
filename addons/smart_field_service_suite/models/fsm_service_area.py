from odoo import fields, models


class FsmServiceArea(models.Model):
    _name = "fsm.service.area"
    _description = "Service Area"
    _order = "name"

    name = fields.Char(required=True, translate=True)
    code = fields.Char()
    active = fields.Boolean(default=True)
    notes = fields.Text()
