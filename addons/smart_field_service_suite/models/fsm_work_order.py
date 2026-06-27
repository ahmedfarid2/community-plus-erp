from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

PRIORITY = [("0", "Low"), ("1", "Medium"), ("2", "High"), ("3", "Critical")]


class FsmWorkOrder(models.Model):
    _name = "fsm.work.order"
    _description = "Field Service Work Order"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc, id desc"

    name = fields.Char(string="Reference", required=True, copy=False,
                       readonly=True, index=True, default=lambda s: "New")
    service_request_id = fields.Many2one("fsm.service.request",
                                         string="Service Request", readonly=True)
    contract_id = fields.Many2one("fsm.maintenance.contract",
                                  string="Maintenance Contract", readonly=True)
    partner_id = fields.Many2one("res.partner", string="Customer",
                                 required=True, tracking=True)
    service_location_id = fields.Many2one("fsm.service.location",
                                          string="Service Location")
    asset_id = fields.Many2one("fsm.customer.asset", string="Asset")
    team_id = fields.Many2one("fsm.team", string="Team", tracking=True)
    technician_id = fields.Many2one("fsm.technician", string="Technician",
                                    tracking=True, index=True)
    secondary_technician_ids = fields.Many2many(
        "fsm.technician", "fsm_wo_secondary_tech_rel",
        string="Secondary Technicians")
    service_type_id = fields.Many2one("fsm.service.type", string="Service Type")
    priority = fields.Selection(PRIORITY, default="1", tracking=True)

    scheduled_start = fields.Datetime(tracking=True)
    scheduled_end = fields.Datetime()
    actual_start = fields.Datetime(readonly=True)
    actual_end = fields.Datetime(readonly=True)
    travel_start = fields.Datetime(readonly=True)
    travel_end = fields.Datetime(readonly=True)

    response_deadline = fields.Datetime(compute="_compute_sla", store=True)
    resolution_deadline = fields.Datetime(compute="_compute_sla", store=True)
    sla_policy_id = fields.Many2one("fsm.sla.policy", compute="_compute_sla",
                                    store=True)
    sla_status = fields.Selection(
        [("on_track", "On Track"), ("warning", "Warning"),
         ("breached", "Breached"), ("completed", "Completed")],
        compute="_compute_sla_status", store=True, tracking=True)

    state = fields.Selection(
        [("draft", "Draft"), ("scheduled", "Scheduled"),
         ("dispatched", "Dispatched"), ("traveling", "Traveling"),
         ("in_progress", "In Progress"), ("waiting_parts", "Waiting Parts"),
         ("waiting_customer", "Waiting Customer"), ("completed", "Completed"),
         ("reviewed", "Reviewed"), ("cancelled", "Cancelled")],
        default="draft", required=True, tracking=True, index=True)

    diagnosis = fields.Text()
    work_performed = fields.Text()
    customer_notes = fields.Text()
    internal_notes = fields.Text()

    checklist_line_ids = fields.One2many("fsm.work.order.checklist.line",
                                         "work_order_id", string="Checklist")
    part_line_ids = fields.One2many("fsm.work.order.part.line",
                                    "work_order_id", string="Parts")
    time_line_ids = fields.One2many("fsm.work.order.time.line",
                                    "work_order_id", string="Time")
    log_ids = fields.One2many("fsm.operation.log", "work_order_id",
                              string="Operation Logs")

    customer_signature = fields.Binary(string="Customer Signature")
    signed_by = fields.Char()
    signed_date = fields.Datetime(readonly=True)

    travel_duration = fields.Float(compute="_compute_durations", store=True)
    work_duration = fields.Float(compute="_compute_durations", store=True)
    total_duration = fields.Float(compute="_compute_durations", store=True)

    currency_id = fields.Many2one(
        "res.currency", default=lambda s: s.env.company.currency_id)
    cost_total = fields.Monetary(compute="_compute_amounts", store=True,
                                 currency_field="currency_id")
    billable_total = fields.Monetary(compute="_compute_amounts", store=True,
                                     currency_field="currency_id")
    profit_total = fields.Monetary(compute="_compute_amounts", store=True,
                                   currency_field="currency_id")

    billable = fields.Boolean(default=True)
    invoice_status = fields.Selection(
        [("not_billable", "Not Billable"), ("to_invoice", "To Invoice"),
         ("invoiced", "Invoiced")], compute="_compute_invoice_status",
        store=True)
    company_id = fields.Many2one("res.company", default=lambda s: s.env.company)

    checklist_count = fields.Integer(compute="_compute_counts")
    part_count = fields.Integer(compute="_compute_counts")
    time_count = fields.Integer(compute="_compute_counts")
    log_count = fields.Integer(compute="_compute_counts")
    skill_warning = fields.Char(compute="_compute_skill_warning")

    # ----------------------------------------------------------- computes
    @api.depends("priority", "create_date")
    def _compute_sla(self):
        for wo in self:
            policy = self.env["fsm.sla.policy"].search(
                [("priority", "=", wo.priority), ("active", "=", True)],
                limit=1)
            wo.sla_policy_id = policy
            base = wo.create_date or fields.Datetime.now()
            if policy:
                wo.response_deadline = base + relativedelta(
                    hours=int(policy.response_time_hours),
                    minutes=int((policy.response_time_hours % 1) * 60))
                wo.resolution_deadline = base + relativedelta(
                    hours=int(policy.resolution_time_hours),
                    minutes=int((policy.resolution_time_hours % 1) * 60))
            else:
                wo.response_deadline = False
                wo.resolution_deadline = False

    @api.depends("state", "response_deadline", "resolution_deadline",
                 "actual_end")
    def _compute_sla_status(self):
        now = fields.Datetime.now()
        for wo in self:
            if wo.state in ("completed", "reviewed"):
                wo.sla_status = "completed"
            elif wo.state == "cancelled":
                wo.sla_status = "completed"
            elif wo.resolution_deadline and now > wo.resolution_deadline:
                wo.sla_status = "breached"
            elif wo.response_deadline and now > wo.response_deadline:
                wo.sla_status = "warning"
            else:
                wo.sla_status = "on_track"

    @api.depends("travel_start", "travel_end", "actual_start", "actual_end")
    def _compute_durations(self):
        for wo in self:
            wo.travel_duration = wo._hours(wo.travel_start, wo.travel_end)
            wo.work_duration = wo._hours(wo.actual_start, wo.actual_end)
            wo.total_duration = wo.travel_duration + wo.work_duration

    @staticmethod
    def _hours(start, end):
        if start and end and end > start:
            return (end - start).total_seconds() / 3600.0
        return 0.0

    @api.depends("part_line_ids.subtotal_cost", "part_line_ids.subtotal_price",
                 "part_line_ids.billable", "time_line_ids.duration_hours",
                 "time_line_ids.billable", "time_line_ids.technician_id")
    def _compute_amounts(self):
        for wo in self:
            parts_cost = sum(wo.part_line_ids.mapped("subtotal_cost"))
            parts_bill = sum(p.subtotal_price for p in wo.part_line_ids
                             if p.billable)
            labor_cost = sum(t.duration_hours * (t.technician_id.hourly_cost or 0.0)
                             for t in wo.time_line_ids)
            labor_bill = sum(t.duration_hours * (t.technician_id.hourly_cost or 0.0)
                             for t in wo.time_line_ids if t.billable)
            wo.cost_total = parts_cost + labor_cost
            wo.billable_total = parts_bill + labor_bill
            wo.profit_total = wo.billable_total - wo.cost_total

    @api.depends("billable", "state", "invoice_status")
    def _compute_invoice_status(self):
        for wo in self:
            if not wo.billable or wo.state == "cancelled":
                wo.invoice_status = "not_billable"
            elif wo.invoice_status == "invoiced":
                wo.invoice_status = "invoiced"
            elif wo.state in ("completed", "reviewed"):
                wo.invoice_status = "to_invoice"
            else:
                wo.invoice_status = "not_billable"

    def _compute_counts(self):
        for wo in self:
            wo.checklist_count = len(wo.checklist_line_ids)
            wo.part_count = len(wo.part_line_ids)
            wo.time_count = len(wo.time_line_ids)
            wo.log_count = len(wo.log_ids)

    @api.depends("technician_id", "service_type_id")
    def _compute_skill_warning(self):
        for wo in self:
            warn = False
            req = wo.service_type_id.skill_ids
            if wo.technician_id and req:
                missing = req - wo.technician_id.skill_ids
                if missing:
                    warn = "Technician is missing skills: %s" % ", ".join(
                        missing.mapped("name"))
            wo.skill_warning = warn

    # ----------------------------------------------------------- onchange
    @api.onchange("service_type_id")
    def _onchange_service_type(self):
        if self.service_type_id:
            if self.service_type_id.default_priority:
                self.priority = self.service_type_id.default_priority
            self.billable = self.service_type_id.billable_by_default

    @api.onchange("asset_id")
    def _onchange_asset(self):
        if self.asset_id:
            self.service_location_id = self.asset_id.service_location_id
            if not self.partner_id:
                self.partner_id = self.asset_id.partner_id

    # -------------------------------------------------------------- create
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "fsm.work.order") or "New"
        orders = super().create(vals_list)
        for wo in orders:
            wo._log("created")
        return orders

    def _log(self, event_type, description=None):
        self.ensure_one()
        self.env["fsm.operation.log"].create({
            "work_order_id": self.id, "event_type": event_type,
            "event_date": fields.Datetime.now(), "user_id": self.env.uid,
            "description": description or dict(
                self._fields["state"].selection).get(self.state, event_type)})

    # ---------------------------------------------------- checklist helper
    def action_load_checklist(self):
        for wo in self:
            tmpl = (wo.service_type_id.checklist_template_id
                    or self.env["fsm.checklist.template"].search(
                        [("service_type_id", "=", wo.service_type_id.id)],
                        limit=1))
            if not tmpl:
                raise UserError("No checklist template for this service type.")
            wo.checklist_line_ids.unlink()
            wo.checklist_line_ids = [(0, 0, {
                "sequence": it.sequence, "name": it.name,
                "is_required": it.is_required,
                "answer_type": it.expected_answer_type,
            }) for it in tmpl.checklist_item_ids]
        return True

    # ----------------------------------------------------- state actions
    def _check_skill_conflict(self):
        for wo in self:
            if wo.technician_id and wo.scheduled_start and not \
                    self.env["ir.config_parameter"].sudo().get_param(
                        "fsm.allow_double_booking") == "1":
                clash = self.search([
                    ("id", "!=", wo.id),
                    ("technician_id", "=", wo.technician_id.id),
                    ("state", "not in", ("completed", "reviewed", "cancelled")),
                    ("scheduled_start", "<", wo.scheduled_end or wo.scheduled_start),
                    ("scheduled_end", ">", wo.scheduled_start)], limit=1)
                if clash:
                    raise UserError(
                        "%s is already booked (%s) for that time."
                        % (wo.technician_id.name, clash.name))

    def action_schedule(self):
        for wo in self:
            if not wo.scheduled_start:
                raise UserError("Set a scheduled start before scheduling.")
            wo._check_skill_conflict()
            wo.write({"state": "scheduled"})
            wo._log("scheduled")

    def action_dispatch(self):
        for wo in self:
            if not wo.technician_id:
                raise UserError("Assign a technician before dispatching.")
            wo.write({"state": "dispatched"})
            wo._log("dispatched")

    def action_start_travel(self):
        self.write({"state": "traveling",
                    "travel_start": fields.Datetime.now()})
        for wo in self:
            wo._log("travel_started")

    def action_start_work(self):
        now = fields.Datetime.now()
        for wo in self:
            vals = {"state": "in_progress", "actual_start": now}
            if wo.travel_start and not wo.travel_end:
                vals["travel_end"] = now
            wo.write(vals)
            wo._log("work_started")

    def action_waiting_parts(self):
        self.write({"state": "waiting_parts"})
        for wo in self:
            wo._log("waiting_parts")

    def action_waiting_customer(self):
        self.write({"state": "waiting_customer"})
        for wo in self:
            wo._log("waiting_customer")

    def action_complete(self):
        for wo in self:
            missing = wo.checklist_line_ids.filtered(
                lambda l: l.is_required and not l.is_done)
            if missing:
                raise UserError(
                    "Complete required checklist items first:\n• "
                    + "\n• ".join(missing.mapped("name")))
            vals = {"state": "completed",
                    "actual_end": fields.Datetime.now()}
            if not wo.actual_start:
                vals["actual_start"] = fields.Datetime.now()
            wo.write(vals)
            wo._log("completed")
            wo._update_asset_history()

    def _update_asset_history(self):
        self.ensure_one()
        if self.asset_id:
            self.asset_id.sudo().write({
                "last_service_date": fields.Date.context_today(self)})

    def action_review(self):
        for wo in self:
            if wo.state != "completed":
                raise UserError("Only completed work orders can be reviewed.")
            wo.write({"state": "reviewed"})
            wo._log("reviewed")

    def action_cancel(self):
        self.write({"state": "cancelled"})
        for wo in self:
            wo._log("cancelled")

    def action_reset_to_draft(self):
        self.write({"state": "draft"})

    def action_sign(self):
        self.write({"signed_date": fields.Datetime.now()})

    # ---------------------------------------------------- constraints
    @api.constrains("actual_start", "actual_end")
    def _check_work_times(self):
        for wo in self:
            if wo.actual_start and wo.actual_end and \
                    wo.actual_end < wo.actual_start:
                raise ValidationError("Work end must be after work start.")

    @api.constrains("travel_start", "travel_end")
    def _check_travel_times(self):
        for wo in self:
            if wo.travel_start and wo.travel_end and \
                    wo.travel_end < wo.travel_start:
                raise ValidationError("Travel end must be after travel start.")

    # ---------------------------------------------------- smart buttons
    def _open(self, model, name, ctx=None):
        self.ensure_one()
        return {"type": "ir.actions.act_window", "name": name,
                "res_model": model, "view_mode": "list,form",
                "domain": [("work_order_id", "=", self.id)],
                "context": {"default_work_order_id": self.id, **(ctx or {})}}

    def action_view_checklist(self):
        return self._open("fsm.work.order.checklist.line", "Checklist")

    def action_view_parts(self):
        return self._open("fsm.work.order.part.line", "Parts")

    def action_view_time(self):
        return self._open("fsm.work.order.time.line", "Time Lines")

    def action_view_logs(self):
        return self._open("fsm.operation.log", "Operation Logs")

    # ------------------------------------------------------------- cron
    @api.model
    def _cron_check_sla(self):
        now = fields.Datetime.now()
        open_orders = self.search([
            ("state", "not in", ("completed", "reviewed", "cancelled"))])
        open_orders._compute_sla_status()
        for wo in open_orders.filtered(lambda w: w.sla_status == "breached"):
            if not wo.activity_ids.filtered(
                    lambda a: a.summary == "SLA breached: %s" % wo.name):
                wo.activity_schedule(
                    "mail.mail_activity_data_todo",
                    user_id=wo.team_id.manager_id.id or wo.create_uid.id,
                    summary="SLA breached: %s" % wo.name,
                    note="Resolution deadline passed.")
                wo._log("sla_breached")


class FsmWorkOrderChecklistLine(models.Model):
    _name = "fsm.work.order.checklist.line"
    _description = "Work Order Checklist Line"
    _order = "sequence, id"

    work_order_id = fields.Many2one("fsm.work.order", required=True,
                                    ondelete="cascade", index=True)
    sequence = fields.Integer(default=10)
    name = fields.Char(required=True)
    is_required = fields.Boolean()
    answer_type = fields.Selection(
        [("yes_no", "Yes / No"), ("text", "Text"), ("number", "Number"),
         ("photo", "Photo"), ("checkbox", "Checkbox")], default="yes_no")
    answer_text = fields.Char()
    answer_number = fields.Float()
    answer_yes_no = fields.Selection([("yes", "Yes"), ("no", "No")])
    is_done = fields.Boolean(string="Done")
    notes = fields.Char()


class FsmWorkOrderPartLine(models.Model):
    _name = "fsm.work.order.part.line"
    _description = "Work Order Part Line"
    _order = "id"

    work_order_id = fields.Many2one("fsm.work.order", required=True,
                                    ondelete="cascade", index=True)
    product_id = fields.Many2one("product.product", string="Product")
    description = fields.Char()
    quantity = fields.Float(default=1.0)
    unit_cost = fields.Monetary(currency_field="currency_id")
    unit_price = fields.Monetary(currency_field="currency_id")
    subtotal_cost = fields.Monetary(compute="_compute_subtotals", store=True,
                                    currency_field="currency_id")
    subtotal_price = fields.Monetary(compute="_compute_subtotals", store=True,
                                     currency_field="currency_id")
    billable = fields.Boolean(default=True)
    currency_id = fields.Many2one(related="work_order_id.currency_id")
    notes = fields.Char()

    @api.depends("quantity", "unit_cost", "unit_price")
    def _compute_subtotals(self):
        for line in self:
            line.subtotal_cost = line.quantity * line.unit_cost
            line.subtotal_price = line.quantity * line.unit_price

    @api.onchange("product_id")
    def _onchange_product(self):
        if self.product_id:
            self.description = self.product_id.display_name
            self.unit_cost = self.product_id.standard_price
            self.unit_price = self.product_id.lst_price


class FsmWorkOrderTimeLine(models.Model):
    _name = "fsm.work.order.time.line"
    _description = "Work Order Time Line"
    _order = "start_time, id"

    work_order_id = fields.Many2one("fsm.work.order", required=True,
                                    ondelete="cascade", index=True)
    technician_id = fields.Many2one("fsm.technician", string="Technician")
    start_time = fields.Datetime()
    end_time = fields.Datetime()
    duration_hours = fields.Float(compute="_compute_duration", store=True)
    time_type = fields.Selection(
        [("travel", "Travel"), ("work", "Work"), ("waiting", "Waiting"),
         ("other", "Other")], default="work")
    billable = fields.Boolean(default=True)
    notes = fields.Char()

    @api.depends("start_time", "end_time")
    def _compute_duration(self):
        for line in self:
            if line.start_time and line.end_time and \
                    line.end_time > line.start_time:
                line.duration_hours = (
                    line.end_time - line.start_time).total_seconds() / 3600.0
            else:
                line.duration_hours = 0.0
