from odoo import fields, models


class FsmTeam(models.Model):
    _name = "fsm.team"
    _description = "Field Service Team"
    _order = "name"

    name = fields.Char(required=True, translate=True)
    manager_id = fields.Many2one("res.users", string="Manager")
    technician_ids = fields.One2many("fsm.technician", "team_id",
                                     string="Technicians")
    service_area_ids = fields.Many2many("fsm.service.area",
                                        string="Service Areas")
    active = fields.Boolean(default=True)
    company_id = fields.Many2one("res.company", default=lambda s: s.env.company)
    notes = fields.Text()
