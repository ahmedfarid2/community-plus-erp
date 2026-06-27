from odoo import fields, models


class FsmSkill(models.Model):
    _name = "fsm.skill"
    _description = "Technician Skill"
    _order = "name"

    name = fields.Char(required=True, translate=True)
    code = fields.Char()
    active = fields.Boolean(default=True)
