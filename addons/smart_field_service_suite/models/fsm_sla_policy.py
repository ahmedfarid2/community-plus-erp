from odoo import fields, models


class FsmSlaPolicy(models.Model):
    _name = "fsm.sla.policy"
    _description = "SLA Policy"
    _order = "priority desc, name"

    name = fields.Char(required=True, translate=True)
    priority = fields.Selection(
        [("0", "Low"), ("1", "Medium"), ("2", "High"), ("3", "Critical")],
        required=True, default="1")
    response_time_hours = fields.Float(
        default=4.0, help="Hours to first response / dispatch.")
    resolution_time_hours = fields.Float(
        default=24.0, help="Hours to resolve / complete.")
    active = fields.Boolean(default=True)
    company_id = fields.Many2one("res.company", default=lambda s: s.env.company)
    notes = fields.Text()
