from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import UserError


class PaymentPlan(models.Model):
    _name = "payment.plan"
    _description = "Payment Plan"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc, id desc"

    name = fields.Char(
        string="Reference", required=True, copy=False, readonly=True,
        index=True, default=lambda self: "New", tracking=True)
    partner_id = fields.Many2one(
        "res.partner", string="Customer", required=True, tracking=True,
        help="The customer who owes the scheduled payments.")
    company_id = fields.Many2one(
        "res.company", string="Company", required=True,
        default=lambda self: self.env.company)
    currency_id = fields.Many2one(
        "res.currency", string="Currency", required=True,
        default=lambda self: self.env.company.currency_id)

    # Generic source document — not tied to any single model.
    source_ref = fields.Reference(
        selection="_selection_source_ref", string="Source Document",
        help="Optional originating document (sales order, invoice, project, "
             "contract…). The list only shows models installed on this database.")

    total_amount = fields.Monetary(
        string="Total Amount", currency_field="currency_id", tracking=True,
        help="Planned total to be collected. Used when generating lines "
             "from a template.")
    paid_amount = fields.Monetary(
        string="Paid Amount", currency_field="currency_id",
        compute="_compute_amounts", store=True)
    remaining_amount = fields.Monetary(
        string="Remaining Amount", currency_field="currency_id",
        compute="_compute_amounts", store=True)
    overdue_amount = fields.Monetary(
        string="Overdue Amount", currency_field="currency_id",
        compute="_compute_overdue", store=True,
        help="Sum of the remaining amounts on lines that are past due "
             "(after the grace period).")

    start_date = fields.Date(
        string="Start Date", default=fields.Date.context_today, tracking=True)
    end_date = fields.Date(string="End Date", tracking=True)
    next_due_date = fields.Date(
        string="Next Due Date", compute="_compute_next_due_date", store=True,
        help="Earliest unpaid line due date.")

    plan_type_id = fields.Many2one(
        "payment.plan.type", string="Plan Type",
        help="Free-form categorization configured by the company.")
    template_id = fields.Many2one(
        "payment.plan.template", string="Template",
        help="Schedule template used to generate the lines.")
    responsible_user_id = fields.Many2one(
        "res.users", string="Responsible", tracking=True,
        default=lambda self: self.env.user,
        help="User accountable for collecting this plan.")

    line_ids = fields.One2many(
        "payment.plan.line", "plan_id", string="Payment Lines", copy=True)
    followup_ids = fields.One2many(
        "collection.followup", "plan_id", string="Follow-ups")

    state = fields.Selection(
        [("draft", "Draft"),
         ("active", "Active"),
         ("closed", "Closed"),
         ("cancelled", "Cancelled")],
        string="Status", default="draft", required=True, tracking=True)
    notes = fields.Text(string="Notes")

    line_count = fields.Integer(compute="_compute_counts")
    overdue_line_count = fields.Integer(compute="_compute_counts")
    followup_count = fields.Integer(compute="_compute_counts")

    @api.model
    def _selection_source_ref(self):
        """Only expose source models that are actually installed, so the core
        module never hard-depends on sale/account/project."""
        candidates = [
            ("sale.order", "Sales Order"),
            ("account.move", "Invoice"),
            ("project.project", "Project"),
            ("subscription.subscription", "Subscription"),
        ]
        return [(model, label) for model, label in candidates
                if model in self.env]

    @api.depends("line_ids.paid_amount", "line_ids.remaining_amount")
    def _compute_amounts(self):
        for plan in self:
            plan.paid_amount = sum(plan.line_ids.mapped("paid_amount"))
            plan.remaining_amount = sum(plan.line_ids.mapped("remaining_amount"))

    @api.depends("line_ids.remaining_amount", "line_ids.status")
    def _compute_overdue(self):
        for plan in self:
            plan.overdue_amount = sum(
                line.remaining_amount for line in plan.line_ids
                if line.status == "overdue")

    @api.depends("line_ids.due_date", "line_ids.remaining_amount",
                 "line_ids.status")
    def _compute_next_due_date(self):
        for plan in self:
            open_lines = plan.line_ids.filtered(
                lambda l: l.status not in ("paid", "cancelled")
                and l.due_date)
            plan.next_due_date = min(
                open_lines.mapped("due_date")) if open_lines else False

    @api.depends("line_ids", "line_ids.status", "followup_ids")
    def _compute_counts(self):
        for plan in self:
            plan.line_count = len(plan.line_ids)
            plan.overdue_line_count = len(plan.line_ids.filtered(
                lambda l: l.status == "overdue"))
            plan.followup_count = len(plan.followup_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "payment.plan") or "New"
        return super().create(vals_list)

    # --- Schedule generation -------------------------------------------------
    def action_generate_lines(self):
        """Generate payment lines from the selected template and total amount."""
        for plan in self:
            if not plan.template_id:
                raise UserError("Select a template before generating lines.")
            if plan.total_amount <= 0:
                raise UserError(
                    "Set a positive Total Amount before generating lines.")
            if plan.line_ids:
                raise UserError(
                    "This plan already has lines. Remove them before "
                    "regenerating from a template.")
            plan.line_ids = [(0, 0, vals) for vals in plan._build_line_vals()]
        return True

    def _build_line_vals(self):
        """Return a list of line value dicts based on the template."""
        self.ensure_one()
        tmpl = self.template_id
        count = max(tmpl.number_of_payments, 1)
        currency = self.currency_id
        start = self.start_date or fields.Date.context_today(self)

        # Amount distribution.
        amounts = []
        if not tmpl.equal_distribution and tmpl.first_payment_percent:
            first = currency.round(
                self.total_amount * tmpl.first_payment_percent / 100.0)
            amounts.append(first)
            rest = self.total_amount - first
            if count > 1:
                each = currency.round(rest / (count - 1))
                amounts += [each] * (count - 1)
        else:
            each = currency.round(self.total_amount / count)
            amounts = [each] * count
        # Absorb rounding drift into the last line so the sum is exact.
        if amounts:
            amounts[-1] += self.total_amount - sum(amounts)
            amounts[-1] = currency.round(amounts[-1])

        steps = {"weekly": relativedelta(weeks=1),
                 "monthly": relativedelta(months=1),
                 "quarterly": relativedelta(months=3),
                 "custom": relativedelta(months=1)}
        step = steps.get(tmpl.frequency, relativedelta(months=1))

        vals = []
        due = start
        for index, amount in enumerate(amounts):
            vals.append({
                "sequence": (index + 1) * 10,
                "due_date": due,
                "amount": amount,
            })
            due = due + step
        return vals

    # --- State transitions ---------------------------------------------------
    def action_activate(self):
        for plan in self:
            if not plan.line_ids:
                raise UserError(
                    "Add at least one payment line before activating.")
        self.write({"state": "active"})

    def action_close(self):
        self.write({"state": "closed"})

    def action_cancel(self):
        self.write({"state": "cancelled"})

    def action_reset_to_draft(self):
        self.write({"state": "draft"})

    # --- Smart buttons -------------------------------------------------------
    def action_view_lines(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Payment Lines",
            "res_model": "payment.plan.line",
            "view_mode": "list,form",
            "domain": [("plan_id", "=", self.id)],
            "context": {"default_plan_id": self.id},
        }

    def action_view_overdue(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Overdue Lines",
            "res_model": "payment.plan.line",
            "view_mode": "list,form",
            "domain": [("plan_id", "=", self.id), ("status", "=", "overdue")],
            "context": {"default_plan_id": self.id},
        }

    def action_view_followups(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Follow-ups",
            "res_model": "collection.followup",
            "view_mode": "list,form",
            "domain": [("plan_id", "=", self.id)],
            "context": {"default_plan_id": self.id,
                        "default_partner_id": self.partner_id.id},
        }
