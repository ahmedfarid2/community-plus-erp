from odoo import fields, models


class FsmTechnician(models.Model):
    _name = "fsm.technician"
    _description = "Field Service Technician"
    _order = "name"

    name = fields.Char(required=True, translate=True)
    user_id = fields.Many2one("res.users", string="Related User")
    phone = fields.Char()
    email = fields.Char()
    team_id = fields.Many2one("fsm.team", string="Team")
    skill_ids = fields.Many2many("fsm.skill", string="Skills")
    service_area_ids = fields.Many2many("fsm.service.area",
                                        string="Service Areas")
    active = fields.Boolean(default=True)
    availability_status = fields.Selection(
        [("available", "Available"), ("busy", "Busy"),
         ("off_duty", "Off Duty"), ("on_leave", "On Leave")],
        default="available")
    hourly_cost = fields.Monetary(currency_field="currency_id")
    currency_id = fields.Many2one(
        "res.currency", default=lambda s: s.env.company.currency_id)
    company_id = fields.Many2one("res.company", default=lambda s: s.env.company)
    notes = fields.Text()
