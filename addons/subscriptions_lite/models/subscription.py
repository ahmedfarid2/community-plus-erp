from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import UserError


class SubscriptionPlan(models.Model):
    _name = "subscription.lite.plan"
    _description = "Subscription Plan"
    _order = "name"

    name = fields.Char(required=True)
    interval_number = fields.Integer(default=1, required=True)
    interval_unit = fields.Selection(
        [("months", "Months"), ("years", "Years")],
        default="months",
        required=True,
    )
    active = fields.Boolean(default=True)


class SubscriptionContract(models.Model):
    _name = "subscription.lite.contract"
    _description = "Subscription Contract"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "next_invoice_date, id"

    name = fields.Char(required=True, tracking=True)
    partner_id = fields.Many2one("res.partner", required=True, tracking=True)
    plan_id = fields.Many2one("subscription.lite.plan", required=True)
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company)
    currency_id = fields.Many2one(related="company_id.currency_id")
    start_date = fields.Date(default=fields.Date.context_today, required=True)
    next_invoice_date = fields.Date(default=fields.Date.context_today, required=True)
    journal_id = fields.Many2one("account.journal", domain=[("type", "=", "sale")])
    line_ids = fields.One2many("subscription.lite.contract.line", "contract_id")
    invoice_count = fields.Integer(compute="_compute_invoice_count")
    state = fields.Selection(
        [("draft", "Draft"), ("active", "Active"), ("paused", "Paused"), ("closed", "Closed")],
        default="draft",
        required=True,
        tracking=True,
    )
    note = fields.Text()
    user_id = fields.Many2one("res.users", string="Salesperson",
                              default=lambda self: self.env.user, tracking=True)
    activated_date = fields.Date(readonly=True, copy=False)
    churned_date = fields.Date(readonly=True, copy=False)
    close_reason_id = fields.Many2one("subscription.lite.close.reason",
                                      string="Close Reason", copy=False)
    parent_id = fields.Many2one("subscription.lite.contract", string="Upsell of",
                                copy=False)
    is_upsell = fields.Boolean(compute="_compute_is_upsell", store=True)
    template_id = fields.Many2one("subscription.lite.template", string="Template")

    @api.depends("parent_id")
    def _compute_is_upsell(self):
        for contract in self:
            contract.is_upsell = bool(contract.parent_id)

    @api.onchange("template_id")
    def _onchange_template_id(self):
        tmpl = self.template_id
        if not tmpl:
            return
        if tmpl.plan_id:
            self.plan_id = tmpl.plan_id
        if tmpl.note:
            self.note = tmpl.note
        self.line_ids = [(5, 0, 0)] + [
            (0, 0, {"name": ln.name, "quantity": ln.quantity,
                    "price_unit": ln.price_unit, "product_id": ln.product_id.id})
            for ln in tmpl.line_ids]

    def action_create_upsell(self):
        self.ensure_one()
        upsell = self.copy({
            "name": (self.name or "") + " (Upsell)",
            "parent_id": self.id, "state": "draft",
            "activated_date": False, "churned_date": False,
        })
        return {
            "type": "ir.actions.act_window",
            "res_model": "subscription.lite.contract",
            "res_id": upsell.id, "view_mode": "form", "target": "current",
        }
    auto_post = fields.Boolean(
        string="Auto-post Invoices",
        default=lambda self: self.env["ir.config_parameter"].sudo().get_param(
            "subscriptions_lite.auto_post_default") in ("True", "true", "1"),
        help="Post generated invoices automatically instead of leaving them in draft.")
    auto_send = fields.Boolean(
        string="Auto-send to Customer", default=False,
        help="Email the posted invoice to the customer automatically (needs SMTP).")
    recurring_total = fields.Monetary(compute="_compute_mrr", store=True)
    mrr = fields.Monetary(string="MRR", compute="_compute_mrr", store=True,
                          help="Monthly Recurring Revenue (period amount normalised to a month).")

    @api.depends("line_ids.quantity", "line_ids.price_unit",
                 "plan_id.interval_unit", "plan_id.interval_number")
    def _compute_mrr(self):
        for contract in self:
            total = sum(l.quantity * l.price_unit for l in contract.line_ids)
            contract.recurring_total = total
            months = contract.plan_id.interval_number or 1
            if contract.plan_id.interval_unit == "years":
                months *= 12
            contract.mrr = (total / months) if months else 0.0

    def _compute_invoice_count(self):
        Move = self.env["account.move"]
        for contract in self:
            contract.invoice_count = Move.search_count([
                ("move_type", "=", "out_invoice"),
                ("invoice_origin", "=", contract.name),
                ("company_id", "=", contract.company_id.id),
            ])

    def _next_date(self):
        self.ensure_one()
        kwargs = {self.plan_id.interval_unit: self.plan_id.interval_number}
        return self.next_invoice_date + relativedelta(**kwargs)

    def action_activate(self):
        today = fields.Date.context_today(self)
        for contract in self:
            if not contract.line_ids:
                raise UserError("Add at least one invoice line before activating.")
            contract.state = "active"
            if not contract.activated_date:
                contract.activated_date = today
            contract.churned_date = False  # reactivation clears churn

    def action_pause(self):
        self.write({"state": "paused"})

    def action_close(self):
        today = fields.Date.context_today(self)
        for contract in self:
            contract.state = "closed"
            contract.churned_date = today

    def action_reset(self):
        self.write({"state": "draft"})

    @api.model
    def _cron_generate_due_invoices(self):
        """Scheduled: invoice every active contract whose next date is due."""
        today = fields.Date.context_today(self)
        due = self.search([("state", "=", "active"),
                           ("next_invoice_date", "<=", today),
                           ("line_ids", "!=", False)])
        count = 0
        for contract in due:
            try:
                # Savepoint isolates a failure to this contract only.
                with self.env.cr.savepoint():
                    contract.action_create_invoice()
                count += 1
            except Exception:  # noqa: BLE001 - skip one bad contract, keep going
                continue
        return count

    def action_create_invoice(self):
        Move = self.env["account.move"]
        created = self.env["account.move"]
        for contract in self:
            if contract.state != "active":
                raise UserError("Only active subscriptions can create invoices.")
            if not contract.line_ids:
                raise UserError("Add invoice lines first.")
            journal = contract.journal_id or self.env["account.journal"].search(
                [("type", "=", "sale"), ("company_id", "=", contract.company_id.id)],
                limit=1)
            if not journal:
                raise UserError("No Sales journal found for %s." % contract.company_id.name)
            invoice_lines = []
            for line in contract.line_ids:
                vals = {
                    "name": line.name or line.product_id.display_name,
                    "quantity": line.quantity,
                    "price_unit": line.price_unit,
                }
                if line.product_id:
                    vals["product_id"] = line.product_id.id
                if line.account_id:
                    vals["account_id"] = line.account_id.id
                invoice_lines.append((0, 0, vals))
            move = Move.create({
                "move_type": "out_invoice",
                "partner_id": contract.partner_id.id,
                "invoice_date": contract.next_invoice_date,
                "invoice_origin": contract.name,
                "journal_id": journal.id,
                "invoice_line_ids": invoice_lines,
            })
            if contract.auto_post:
                move.action_post()
                if contract.auto_send:
                    contract._send_invoice_email(move)
            contract.next_invoice_date = contract._next_date()
            created |= move
        return {
            "type": "ir.actions.act_window",
            "name": "Invoices",
            "res_model": "account.move",
            "view_mode": "list,form",
            "domain": [("id", "in", created.ids)],
        }

    def _send_invoice_email(self, move):
        """Email the posted invoice to the customer (best-effort; needs SMTP)."""
        self.ensure_one()
        template = self.env.ref("account.email_template_edi_invoice",
                                raise_if_not_found=False)
        try:
            if template:
                template.send_mail(move.id, force_send=False)
            elif move.partner_id:
                move.message_post(
                    body="Invoice %s is available." % move.name,
                    partner_ids=move.partner_id.ids)
        except Exception:  # noqa: BLE001 - SMTP not configured / transient
            pass


class SubscriptionContractLine(models.Model):
    _name = "subscription.lite.contract.line"
    _description = "Subscription Contract Line"
    _order = "sequence, id"

    sequence = fields.Integer(default=10)
    contract_id = fields.Many2one("subscription.lite.contract", ondelete="cascade", required=True)
    product_id = fields.Many2one("product.product")
    name = fields.Char(required=True)
    quantity = fields.Float(default=1.0, required=True)
    currency_id = fields.Many2one(related="contract_id.currency_id")
    price_unit = fields.Monetary(required=True)
    account_id = fields.Many2one("account.account", domain=[("account_type", "=", "income")])

    @api.onchange("product_id")
    def _onchange_product_id(self):
        for line in self:
            if line.product_id:
                line.name = line.product_id.display_name
                line.price_unit = line.product_id.lst_price
