from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import UserError

from .subscription_plan import period_delta, period_months

ACTIVITY_TODO = "mail.mail_activity_data_todo"


class Subscription(models.Model):
    _name = "subscription.subscription"
    _description = "Subscription"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc, id desc"

    name = fields.Char(
        string="Reference", required=True, copy=False, readonly=True,
        index=True, default=lambda s: "New")
    partner_id = fields.Many2one("res.partner", string="Customer",
                                 required=True, tracking=True)
    company_id = fields.Many2one(
        "res.company", default=lambda s: s.env.company, required=True)
    currency_id = fields.Many2one(
        "res.currency", required=True,
        default=lambda s: s.env.company.currency_id)
    plan_id = fields.Many2one("subscription.plan", string="Plan",
                              required=True, tracking=True)
    responsible_user_id = fields.Many2one(
        "res.users", string="Responsible", default=lambda s: s.env.user,
        tracking=True)

    start_date = fields.Date(default=fields.Date.context_today, tracking=True)
    trial_end_date = fields.Date()
    next_billing_date = fields.Date(tracking=True)
    renewal_date = fields.Date(tracking=True)
    end_date = fields.Date(tracking=True)

    billing_period = fields.Selection(
        related="plan_id.billing_period", store=True, readonly=False)
    billing_interval = fields.Integer(
        related="plan_id.billing_interval", store=True, readonly=False)
    recurring_price = fields.Monetary(currency_field="currency_id",
                                      tracking=True)
    setup_fee = fields.Monetary(currency_field="currency_id")
    discount_amount = fields.Monetary(currency_field="currency_id")
    discount_percent = fields.Float(string="Discount (%)")

    current_amount = fields.Monetary(
        currency_field="currency_id", compute="_compute_amounts", store=True,
        help="Net recurring price per billing period after discounts.")
    mrr_amount = fields.Monetary(
        currency_field="currency_id", compute="_compute_amounts", store=True,
        string="MRR")
    arr_amount = fields.Monetary(
        currency_field="currency_id", compute="_compute_amounts", store=True,
        string="ARR")

    state = fields.Selection(
        [("draft", "Draft"), ("trial", "Trial"), ("active", "Active"),
         ("paused", "Paused"), ("expired", "Expired"),
         ("cancelled", "Cancelled"), ("closed", "Closed")],
        default="draft", required=True, tracking=True, index=True)
    auto_renew = fields.Boolean(string="Auto Renew", default=True)
    invoice_policy = fields.Selection(
        [("manual", "Manual"), ("scheduled", "Scheduled"),
         ("automatic", "Automatic")],
        default="manual", required=True)
    payment_status = fields.Selection(
        [("unpaid", "Unpaid"), ("partially_paid", "Partially Paid"),
         ("paid", "Paid"), ("overdue", "Overdue")],
        compute="_compute_payment_status", store=True)
    health = fields.Selection(
        [("healthy", "Healthy"), ("at_risk", "At Risk"),
         ("overdue", "Overdue"), ("churned", "Churned")],
        compute="_compute_health", store=True)

    billing_line_ids = fields.One2many(
        "subscription.billing.line", "subscription_id", string="Billing Lines")
    lifecycle_event_ids = fields.One2many(
        "subscription.lifecycle.event", "subscription_id",
        string="Lifecycle Events")
    pause_ids = fields.One2many(
        "subscription.pause", "subscription_id", string="Pauses")
    change_ids = fields.One2many(
        "subscription.change", "subscription_id", string="Plan Changes")
    cancellation_reason_id = fields.Many2one(
        "subscription.cancellation.reason", string="Cancellation Reason")
    notes = fields.Text()

    billing_count = fields.Integer(compute="_compute_counts")
    event_count = fields.Integer(compute="_compute_counts")
    pause_count = fields.Integer(compute="_compute_counts")
    change_count = fields.Integer(compute="_compute_counts")

    # --------------------------------------------------------------- computes
    @api.depends("recurring_price", "discount_amount", "discount_percent",
                 "billing_period", "billing_interval", "state")
    def _compute_amounts(self):
        for sub in self:
            net = sub.recurring_price * (1 - (sub.discount_percent or 0.0) / 100.0)
            net -= sub.discount_amount or 0.0
            sub.current_amount = max(net, 0.0)
            months = period_months(sub.billing_period, sub.billing_interval)
            mrr = (sub.current_amount / months) if months else 0.0
            active = sub.state in ("trial", "active", "paused")
            sub.mrr_amount = mrr if active else 0.0
            sub.arr_amount = sub.mrr_amount * 12.0

    @api.depends("billing_line_ids.state", "billing_line_ids.remaining_amount")
    def _compute_payment_status(self):
        for sub in self:
            lines = sub.billing_line_ids.filtered(
                lambda l: l.state not in ("skipped", "cancelled"))
            if not lines:
                sub.payment_status = "unpaid"
            elif any(l.state == "overdue" for l in lines):
                sub.payment_status = "overdue"
            elif all(l.state == "paid" for l in lines):
                sub.payment_status = "paid"
            elif any(l.paid_amount > 0 for l in lines):
                sub.payment_status = "partially_paid"
            else:
                sub.payment_status = "unpaid"

    @api.depends("state", "payment_status", "auto_renew", "renewal_date")
    def _compute_health(self):
        today = fields.Date.context_today(self)
        for sub in self:
            if sub.state in ("cancelled", "closed", "expired"):
                sub.health = "churned"
            elif sub.payment_status == "overdue":
                sub.health = "overdue"
            elif sub.state == "trial":
                sub.health = "at_risk"
            elif (sub.state == "active" and not sub.auto_renew
                  and sub.renewal_date
                  and sub.renewal_date <= today + relativedelta(days=30)):
                sub.health = "at_risk"
            elif sub.state == "active":
                sub.health = "healthy"
            else:
                sub.health = "at_risk"

    def _compute_counts(self):
        for sub in self:
            sub.billing_count = len(sub.billing_line_ids)
            sub.event_count = len(sub.lifecycle_event_ids)
            sub.pause_count = len(sub.pause_ids)
            sub.change_count = len(sub.change_ids)

    # ---------------------------------------------------------------- onchange
    @api.onchange("plan_id")
    def _onchange_plan_id(self):
        if self.plan_id:
            p = self.plan_id
            self.recurring_price = p.price
            self.setup_fee = p.setup_fee
            self.currency_id = p.currency_id
            self.auto_renew = p.auto_renew
            if p.trial_days and self.start_date:
                self.trial_end_date = self.start_date + relativedelta(
                    days=p.trial_days)

    # ------------------------------------------------------------------ create
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "subscription.subscription") or "New"
            if vals.get("plan_id") and not vals.get("recurring_price"):
                plan = self.env["subscription.plan"].browse(vals["plan_id"])
                vals.setdefault("recurring_price", plan.price)
                vals.setdefault("setup_fee", plan.setup_fee)
        subs = super().create(vals_list)
        for sub in subs:
            sub._log_event("created")
        return subs

    # ----------------------------------------------------------------- helpers
    def _log_event(self, event_type, old_plan=None, new_plan=None,
                   old_amount=None, new_amount=None, reason=None, notes=None):
        self.ensure_one()
        self.env["subscription.lifecycle.event"].create({
            "subscription_id": self.id,
            "event_type": event_type,
            "event_date": fields.Datetime.now(),
            "user_id": self.env.user.id,
            "old_plan_id": old_plan.id if old_plan else False,
            "new_plan_id": new_plan.id if new_plan else False,
            "old_amount": old_amount or 0.0,
            "new_amount": new_amount or 0.0,
            "reason": reason or "",
            "notes": notes or "",
        })

    def _term_delta(self):
        self.ensure_one()
        if self.plan_id.minimum_contract_months:
            return relativedelta(months=self.plan_id.minimum_contract_months)
        return period_delta(self.billing_period, self.billing_interval)

    def _check_activatable(self):
        self.ensure_one()
        if not (self.partner_id and self.plan_id and self.start_date):
            raise UserError(
                "Customer, plan and start date are required to activate.")
        if self.recurring_price < 0:
            raise UserError("The recurring price cannot be negative.")

    # ----------------------------------------------------------- state actions
    def action_start_trial(self):
        for sub in self:
            sub._check_activatable()
            if not sub.trial_end_date:
                days = sub.plan_id.trial_days or 14
                sub.trial_end_date = sub.start_date + relativedelta(days=days)
            sub.write({"state": "trial"})
            sub._log_event("trial_started")

    def action_activate(self):
        for sub in self:
            sub._check_activatable()
            if not sub.next_billing_date:
                sub.next_billing_date = sub.trial_end_date or sub.start_date
            if not sub.renewal_date:
                sub.renewal_date = (sub.start_date + sub._term_delta())
            if not sub.end_date and not sub.auto_renew:
                sub.end_date = sub.renewal_date
            was_trial = sub.state == "trial"
            sub.write({"state": "active"})
            sub._log_event("trial_ended" if was_trial else "activated")

    def action_generate_billing(self):
        for sub in self:
            sub._generate_billing_lines()

    def _generate_billing_lines(self):
        self.ensure_one()
        if self.state in ("cancelled", "closed", "expired"):
            raise UserError(
                "Cannot generate billing for a %s subscription." % self.state)
        if self.state == "paused":
            raise UserError("Resume the subscription before billing.")
        start = self.next_billing_date or self.trial_end_date or self.start_date
        if not start:
            raise UserError("Set a start/next billing date first.")
        delta = period_delta(self.billing_period, self.billing_interval)
        existing = set(self.billing_line_ids.mapped("period_start_date"))

        if self.end_date:
            n_periods = 60
        elif self.plan_id.minimum_contract_months:
            pm = period_months(self.billing_period, self.billing_interval)
            n_periods = max(1, round(self.plan_id.minimum_contract_months / pm))
        else:
            n_periods = 12

        vals, seq, period_start = [], len(self.billing_line_ids), start
        for _i in range(n_periods):
            if self.end_date and period_start > self.end_date:
                break
            period_end = period_start + delta - relativedelta(days=1)
            if period_start not in existing:
                seq += 1
                vals.append({
                    "subscription_id": self.id, "sequence": seq * 10,
                    "period_start_date": period_start,
                    "period_end_date": period_end,
                    "billing_date": period_start,
                    "due_date": period_start + relativedelta(
                        days=self.plan_id.grace_period_days or 0),
                    "amount": self.current_amount, "state": "due",
                })
            period_start = period_start + delta
        self.env["subscription.billing.line"].create(vals)
        self.next_billing_date = period_start
        self._log_event("billing_generated",
                        notes="%s billing line(s) generated" % len(vals))

    def action_renew(self):
        for sub in self:
            sub._do_renew(auto=False)

    def _do_renew(self, auto=False):
        self.ensure_one()
        if self.renewal_date:
            self.renewal_date = self.renewal_date + self._term_delta()
        if self.end_date:
            self.end_date = self.end_date + self._term_delta()
        if self.state in ("expired",):
            self.state = "active"
        self._log_event("renewed", notes="Auto-renewed" if auto else "Renewed")

    def action_pause(self):
        for sub in self:
            if sub.state != "active":
                raise UserError("Only active subscriptions can be paused.")
            sub.env["subscription.pause"].create({
                "subscription_id": sub.id,
                "pause_start_date": fields.Date.context_today(sub),
                "state": "active"})
            sub.write({"state": "paused"})
            sub._log_event("paused")

    def action_resume(self):
        for sub in self:
            if sub.state != "paused":
                raise UserError("Only paused subscriptions can be resumed.")
            today = fields.Date.context_today(sub)
            open_pause = sub.pause_ids.filtered(lambda p: p.state == "active")[:1]
            if open_pause:
                open_pause.write({"pause_end_date": today, "state": "completed"})
            sub.write({"state": "active"})
            sub._log_event("resumed")

    def action_open_cancel_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Cancel Subscription",
            "res_model": "subscription.cancel.wizard",
            "view_mode": "form", "target": "new",
            "context": {"default_subscription_id": self.id},
        }

    def action_open_change_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Change Plan",
            "res_model": "subscription.change.wizard",
            "view_mode": "form", "target": "new",
            "context": {"default_subscription_id": self.id},
        }

    def _set_cancelled(self, reason=None, note=None):
        self.ensure_one()
        self.write({"state": "cancelled",
                    "cancellation_reason_id": reason.id if reason else False})
        self.billing_line_ids.filtered(
            lambda l: l.state in ("draft", "due")).write({"state": "cancelled"})
        self._log_event("cancelled",
                        reason=reason.name if reason else "", notes=note)

    def _set_expired(self):
        self.ensure_one()
        self.write({"state": "expired"})
        self._log_event("expired")

    def action_close(self):
        for sub in self:
            sub.write({"state": "closed"})
            sub._log_event("note", notes="Subscription closed")

    def action_reset_to_draft(self):
        self.write({"state": "draft"})

    # --------------------------------------------------------------- renewals
    def _ensure_renewal_activity(self):
        self.ensure_one()
        existing = self.activity_ids.filtered(
            lambda a: a.summary and a.summary.startswith("Renewal due"))
        if existing:
            return
        self.activity_schedule(
            ACTIVITY_TODO, date_deadline=self.renewal_date,
            user_id=self.responsible_user_id.id or self.env.uid,
            summary="Renewal due: %s" % self.name,
            note="This subscription renews on %s." % self.renewal_date)

    # ------------------------------------------------------------ smart buttons
    def _open(self, model, name, ctx=None):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window", "name": name, "res_model": model,
            "view_mode": "list,form",
            "domain": [("subscription_id", "=", self.id)],
            "context": {"default_subscription_id": self.id, **(ctx or {})},
        }

    def action_view_billing(self):
        return self._open("subscription.billing.line", "Billing Lines")

    def action_view_events(self):
        return self._open("subscription.lifecycle.event", "Lifecycle Events")

    def action_view_pauses(self):
        return self._open("subscription.pause", "Pauses")

    def action_view_changes(self):
        return self._open("subscription.change", "Plan Changes")

    def action_view_partner(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window", "res_model": "res.partner",
            "res_id": self.partner_id.id, "view_mode": "form",
            "target": "current",
        }

    # ------------------------------------------------------------------- crons
    @api.model
    def _cron_subscription_maintenance(self):
        today = fields.Date.context_today(self)
        for sub in self.search([("state", "=", "trial"),
                                ("trial_end_date", "<=", today)]):
            sub.action_activate()
        for sub in self.search([("state", "in", ("active",)),
                                ("auto_renew", "=", False),
                                ("end_date", "!=", False),
                                ("end_date", "<", today)]):
            sub._set_expired()
        for sub in self.search([("state", "=", "active"),
                                ("auto_renew", "=", True),
                                ("renewal_date", "!=", False),
                                ("renewal_date", "<=", today)]):
            sub._do_renew(auto=True)
        self.env["subscription.billing.line"].search([
            ("state", "in", ("due", "partially_paid")),
            ("due_date", "<", today),
            ("remaining_amount", ">", 0)]).write({"state": "overdue"})
        soon = today + relativedelta(days=14)
        for sub in self.search([("state", "=", "active"),
                                ("auto_renew", "=", False),
                                ("renewal_date", ">=", today),
                                ("renewal_date", "<=", soon)]):
            sub._ensure_renewal_activity()

    @api.model
    def _cron_snapshot_metrics(self):
        self.env["subscription.metric.snapshot"].generate_snapshot()
