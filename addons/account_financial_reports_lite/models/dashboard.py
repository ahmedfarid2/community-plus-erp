from odoo import api, fields, models


class Dashboard(models.TransientModel):
    _name = "afr.dashboard"
    _description = "Accounting Overview Dashboard"

    company_id = fields.Many2one("res.company", default=lambda s: s.env.company)
    currency_id = fields.Many2one(related="company_id.currency_id")

    cash_balance = fields.Monetary(compute="_compute_kpis")
    receivable = fields.Monetary(compute="_compute_kpis")
    payable = fields.Monetary(compute="_compute_kpis")
    revenue_ytd = fields.Monetary(compute="_compute_kpis")
    expense_ytd = fields.Monetary(compute="_compute_kpis")
    net_profit_ytd = fields.Monetary(compute="_compute_kpis")
    unpaid_invoice_count = fields.Integer(compute="_compute_kpis")
    unpaid_invoice_amount = fields.Monetary(compute="_compute_kpis")
    overdue_amount = fields.Monetary(compute="_compute_kpis")
    bill_to_pay_count = fields.Integer(compute="_compute_kpis")
    bill_to_pay_amount = fields.Monetary(compute="_compute_kpis")

    def _balance(self, types, ytd=False):
        dom = [("company_id", "=", self.company_id.id),
               ("parent_state", "=", "posted"),
               ("account_id.account_type", "in", types)]
        if ytd:
            year_start = fields.Date.context_today(self).replace(month=1, day=1)
            dom.append(("date", ">=", year_start))
        return sum(self.env["account.move.line"].search(dom).mapped("balance"))

    @api.depends("company_id")
    def _compute_kpis(self):
        today = fields.Date.context_today(self)
        Move = self.env["account.move"]
        for d in self:
            d.cash_balance = d._balance(["asset_cash"])
            d.receivable = d._balance(["asset_receivable"])
            d.payable = -d._balance(["liability_payable"])
            d.revenue_ytd = -d._balance(["income", "income_other"], ytd=True)
            d.expense_ytd = d._balance(
                ["expense", "expense_depreciation", "expense_direct_cost"], ytd=True)
            d.net_profit_ytd = d.revenue_ytd - d.expense_ytd

            base = [("company_id", "=", d.company_id.id), ("state", "=", "posted"),
                    ("payment_state", "in", ("not_paid", "partial"))]
            inv = Move.search(base + [("move_type", "=", "out_invoice")])
            d.unpaid_invoice_count = len(inv)
            d.unpaid_invoice_amount = sum(inv.mapped("amount_residual"))
            d.overdue_amount = sum(inv.filtered(
                lambda m: m.invoice_date_due and m.invoice_date_due < today
            ).mapped("amount_residual"))

            bills = Move.search(base + [("move_type", "=", "in_invoice")])
            d.bill_to_pay_count = len(bills)
            d.bill_to_pay_amount = sum(bills.mapped("amount_residual"))

    def action_refresh(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": "afr.dashboard",
            "view_mode": "form",
            "target": "current",
        }
