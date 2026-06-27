from odoo import api, fields, models


class FsmCustomerAsset(models.Model):
    _name = "fsm.customer.asset"
    _description = "Customer Asset"
    _inherit = ["mail.thread"]
    _order = "name"

    name = fields.Char(required=True, tracking=True)
    partner_id = fields.Many2one("res.partner", string="Customer", required=True)
    service_location_id = fields.Many2one("fsm.service.location",
                                          string="Service Location")
    asset_type_id = fields.Many2one("fsm.asset.type", string="Asset Type")
    serial_number = fields.Char()
    model = fields.Char()
    manufacturer = fields.Char()
    installation_date = fields.Date()
    warranty_start_date = fields.Date()
    warranty_end_date = fields.Date()
    status = fields.Selection(
        [("active", "Active"), ("inactive", "Inactive"),
         ("under_maintenance", "Under Maintenance"), ("retired", "Retired")],
        default="active", tracking=True)
    last_service_date = fields.Date(readonly=True)
    next_service_date = fields.Date()
    work_order_ids = fields.One2many("fsm.work.order", "asset_id",
                                     string="Work Orders")
    work_order_count = fields.Integer(compute="_compute_counts")
    contract_count = fields.Integer(compute="_compute_counts")
    company_id = fields.Many2one("res.company", default=lambda s: s.env.company)
    notes = fields.Text()

    def _compute_counts(self):
        wo = {}
        if self.ids:
            for a, c in self.env["fsm.work.order"]._read_group(
                    [("asset_id", "in", self.ids)], ["asset_id"], ["__count"]):
                wo[a.id] = c
        for asset in self:
            asset.work_order_count = wo.get(asset.id, 0)
            asset.contract_count = self.env["fsm.maintenance.contract"]\
                .search_count([("asset_ids", "in", asset.id)])

    def action_view_work_orders(self):
        self.ensure_one()
        return {"type": "ir.actions.act_window", "name": "Service History",
                "res_model": "fsm.work.order", "view_mode": "list,form",
                "domain": [("asset_id", "=", self.id)],
                "context": {"default_asset_id": self.id,
                            "default_partner_id": self.partner_id.id}}

    def action_view_contracts(self):
        self.ensure_one()
        return {"type": "ir.actions.act_window", "name": "Maintenance Contracts",
                "res_model": "fsm.maintenance.contract", "view_mode": "list,form",
                "domain": [("asset_ids", "in", self.id)]}
