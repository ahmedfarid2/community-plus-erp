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
        for contract in self:
            if not contract.line_ids:
                raise UserError("Add at least one invoice line before activating.")
        self.write({"state": "active"})

    def action_pause(self):
        self.write({"state": "paused"})

    def action_close(self):
        self.write({"state": "closed"})

    def action_reset(self):
        self.write({"state": "draft"})

    def action_create_invoice(self):
        Move = self.env["account.move"]
        created = self.env["account.move"]
        for contract in self:
            if contract.state != "active":
                raise UserError("Only active subscriptions can create invoices.")
            if not contract.line_ids:
                raise UserError("Add invoice lines first.")
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
                "journal_id": contract.journal_id.id or False,
                "invoice_line_ids": invoice_lines,
            })
            contract.next_invoice_date = contract._next_date()
            created |= move
        return {
            "type": "ir.actions.act_window",
            "name": "Invoices",
            "res_model": "account.move",
            "view_mode": "list,form",
            "domain": [("id", "in", created.ids)],
        }


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
