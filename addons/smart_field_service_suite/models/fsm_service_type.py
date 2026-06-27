from odoo import fields, models


class FsmServiceType(models.Model):
    _name = "fsm.service.type"
    _description = "Service Type"
    _order = "name"

    name = fields.Char(required=True, translate=True)
    code = fields.Char()
    default_duration_hours = fields.Float(default=1.0)
    default_priority = fields.Selection(
        [("0", "Low"), ("1", "Medium"), ("2", "High"), ("3", "Critical")],
        default="1")
    billable_by_default = fields.Boolean(default=True)
    checklist_template_id = fields.Many2one(
        "fsm.checklist.template", string="Checklist Template")
    skill_ids = fields.Many2many("fsm.skill", string="Required Skills")
    active = fields.Boolean(default=True)
    notes = fields.Text()
