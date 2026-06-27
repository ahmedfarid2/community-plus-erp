from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import UserError

FREQ = [("weekly", "Weekly"), ("monthly", "Monthly"), ("quarterly", "Quarterly"),
        ("semi_annual", "Semi-annual"), ("annual", "Annual"), ("custom", "Custom")]


def freq_delta(frequency, interval):
    interval = max(interval or 1, 1)
    return {
        "weekly": relativedelta(weeks=interval),
        "monthly": relativedelta(months=interval),
        "quarterly": relativedelta(months=3 * interval),
        "semi_annual": relativedelta(months=6 * interval),
        "annual": relativedelta(years=interval),
        "custom": relativedelta(months=interval),
    }.get(frequency, relativedelta(months=interval))


class FsmMaintenanceContract(models.Model):
    _name = "fsm.maintenance.contract"
    _description = "Maintenance Contract"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name"

    name = fields.Char(required=True, copy=False, readonly=True,
                       default=lambda s: "New", tracking=True)
    partner_id = fields.Many2one("res.partner", string="Customer",
                                 required=True, tracking=True)
    service_location_id = fields.Many2one("fsm.service.location",
                                          string="Service Location")
    asset_ids = fields.Many2many("fsm.customer.asset", string="Assets")
    contract_start_date = fields.Date(default=fields.Date.context_today)
    contract_end_date = fields.Date()
    next_service_date = fields.Date(tracking=True)
    recurrence_frequency = fields.Selection(FREQ, default="quarterly",
                                            required=True)
    recurrence_interval = fields.Integer(default=1, required=True)
    service_type_id = fields.Many2one("fsm.service.type", string="Service Type")
    assigned_team_id = fields.Many2one("fsm.team", string="Team")
    assigned_technician_id = fields.Many2one("fsm.technician",
                                             string="Technician")
    auto_generate_work_orders = fields.Boolean(default=True)
    state = fields.Selection(
        [("draft", "Draft"), ("active", "Active"), ("expired", "Expired"),
         ("cancelled", "Cancelled")], default="draft", required=True,
        tracking=True)
    renewal_reminder_days = fields.Integer(default=30)
    service_line_ids = fields.One2many("fsm.contract.service.line",
                                       "contract_id", string="Service Lines")
    work_order_ids = fields.One2many("fsm.work.order", "contract_id",
                                     string="Work Orders")
    work_order_count = fields.Integer(compute="_compute_counts")
    company_id = fields.Many2one("res.company", default=lambda s: s.env.company)
    notes = fields.Text()

    def _compute_counts(self):
        data = {}
        if self.ids:
            for c, n in self.env["fsm.work.order"]._read_group(
                    [("contract_id", "in", self.ids)], ["contract_id"],
                    ["__count"]):
                data[c.id] = n
        for contract in self:
            contract.work_order_count = data.get(contract.id, 0)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "fsm.maintenance.contract") or "New"
        return super().create(vals_list)

    def action_activate(self):
        for c in self:
            if not c.next_service_date:
                c.next_service_date = (c.contract_start_date
                                       or fields.Date.context_today(c))
            c.state = "active"

    def action_expire(self):
        self.write({"state": "expired"})

    def action_cancel(self):
        self.write({"state": "cancelled"})

    def action_reset_to_draft(self):
        self.write({"state": "draft"})

    def action_renew(self):
        for c in self:
            if c.contract_end_date:
                c.contract_end_date = c.contract_end_date + freq_delta(
                    "annual", 1)
            c.state = "active"
            c.message_post(body="Contract renewed.")

    def action_generate_next_work_order(self):
        for c in self:
            c._generate_work_order(c.next_service_date
                                   or fields.Date.context_today(c))
        return True

    def _generate_work_order(self, service_date):
        self.ensure_one()
        # avoid duplicate for same contract + service date
        exists = self.env["fsm.work.order"].search([
            ("contract_id", "=", self.id),
            ("scheduled_start", ">=", fields.Datetime.to_string(
                fields.Datetime.to_datetime(service_date))),
            ("scheduled_start", "<", fields.Datetime.to_string(
                fields.Datetime.to_datetime(service_date)
                + relativedelta(days=1)))], limit=1)
        if exists:
            return exists
        wo = self.env["fsm.work.order"].create({
            "contract_id": self.id,
            "partner_id": self.partner_id.id,
            "service_location_id": self.service_location_id.id,
            "asset_id": self.asset_ids[:1].id,
            "service_type_id": self.service_type_id.id,
            "team_id": self.assigned_team_id.id,
            "technician_id": self.assigned_technician_id.id,
            "scheduled_start": fields.Datetime.to_datetime(service_date),
            "state": "scheduled",
        })
        self.next_service_date = service_date + freq_delta(
            self.recurrence_frequency, self.recurrence_interval)
        self.message_post(body="Generated work order %s." % wo.name)
        return wo

    def action_view_work_orders(self):
        self.ensure_one()
        return {"type": "ir.actions.act_window", "name": "Work Orders",
                "res_model": "fsm.work.order", "view_mode": "list,form",
                "domain": [("contract_id", "=", self.id)],
                "context": {"default_contract_id": self.id,
                            "default_partner_id": self.partner_id.id}}

    # ----------------------------------------------------------------- crons
    @api.model
    def _cron_generate_work_orders(self):
        today = fields.Date.context_today(self)
        for c in self.search([("state", "=", "active"),
                              ("auto_generate_work_orders", "=", True),
                              ("next_service_date", "!=", False),
                              ("next_service_date", "<=", today)]):
            if c.contract_end_date and c.next_service_date > c.contract_end_date:
                c.action_expire()
                continue
            c._generate_work_order(c.next_service_date)

    @api.model
    def _cron_renewal_reminders(self):
        today = fields.Date.context_today(self)
        for c in self.search([("state", "=", "active"),
                              ("contract_end_date", "!=", False)]):
            remind_on = c.contract_end_date - relativedelta(
                days=c.renewal_reminder_days or 30)
            if today >= remind_on and not c.activity_ids.filtered(
                    lambda a: a.summary == "Contract renewal: %s" % c.name):
                c.activity_schedule(
                    "mail.mail_activity_data_todo",
                    date_deadline=c.contract_end_date,
                    summary="Contract renewal: %s" % c.name,
                    note="This maintenance contract expires on %s."
                    % c.contract_end_date)


class FsmContractServiceLine(models.Model):
    _name = "fsm.contract.service.line"
    _description = "Contract Service Line"
    _order = "id"

    contract_id = fields.Many2one("fsm.maintenance.contract", required=True,
                                  ondelete="cascade", index=True)
    service_type_id = fields.Many2one("fsm.service.type", string="Service Type")
    asset_id = fields.Many2one("fsm.customer.asset", string="Asset")
    frequency = fields.Selection(FREQ, default="quarterly")
    interval = fields.Integer(default=1)
    next_service_date = fields.Date()
    last_service_date = fields.Date()
    notes = fields.Char()
