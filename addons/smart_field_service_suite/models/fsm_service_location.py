from odoo import api, fields, models


class FsmServiceLocation(models.Model):
    _name = "fsm.service.location"
    _description = "Service Location"
    _order = "name"

    name = fields.Char(required=True)
    partner_id = fields.Many2one("res.partner", string="Customer", required=True)
    address = fields.Char()
    city = fields.Char()
    state_id = fields.Many2one("res.country.state", string="State")
    country_id = fields.Many2one("res.country", string="Country")
    latitude = fields.Float(digits=(10, 7))
    longitude = fields.Float(digits=(10, 7))
    access_instructions = fields.Text()
    contact_name = fields.Char()
    contact_phone = fields.Char()
    active = fields.Boolean(default=True)
    company_id = fields.Many2one("res.company", default=lambda s: s.env.company)
    notes = fields.Text()

    @api.onchange("partner_id")
    def _onchange_partner(self):
        if self.partner_id:
            p = self.partner_id
            self.address = p.contact_address_complete or p.street
            self.city = p.city
            self.state_id = p.state_id
            self.country_id = p.country_id
            if not self.name:
                self.name = p.name
