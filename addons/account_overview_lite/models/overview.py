from odoo import api, fields, models


class AccountOverview(models.TransientModel):
    _name = "account.overview.board"
    _description = "Accounting Overview"

    company_id = fields.Many2one("res.company", default=lambda s: s.env.company)
    company_name = fields.Char(related="company_id.name")
    currency_id = fields.Many2one(related="company_id.currency_id")

    # Position
    cash = fields.Monetary(compute="_compute_kpis")
    receivable = fields.Monetary(compute="_compute_kpis")
    payable = fields.Monetary(compute="_compute_kpis")
    working_capital = fields.Monetary(compute="_compute_kpis")
    # P&L
    revenue_ytd = fields.Monetary(compute="_compute_kpis")
    expense_ytd = fields.Monetary(compute="_compute_kpis")
    net_profit_ytd = fields.Monetary(compute="_compute_kpis")
    revenue_month = fields.Monetary(compute="_compute_kpis")
    # AR / AP
    unpaid_inv_amount = fields.Monetary(compute="_compute_kpis")
    overdue_amount = fields.Monetary(compute="_compute_kpis")
    unpaid_bill_amount = fields.Monetary(compute="_compute_kpis")
    # Tax
    tax_due = fields.Monetary(compute="_compute_kpis")

    @api.depends("company_id")
    def _compute_kpis(self):
        today = fields.Date.context_today(self)
        AML = self.env["account.move.line"]
        Move = self.env["account.move"]
        for d in self:
            cid = d.company_id.id

            def bal(types, ytd=False, month=False):
                dom = [("company_id", "=", cid), ("parent_state", "=", "posted"),
                       ("account_id.account_type", "in", types)]
                if ytd:
                    dom.append(("date", ">=", today.replace(month=1, day=1)))
                if month:
                    dom.append(("date", ">=", today.replace(day=1)))
                return sum(AML.search(dom).mapped("balance"))

            d.cash = bal(["asset_cash"])
            d.receivable = bal(["asset_receivable"])
            d.payable = -bal(["liability_payable"])
            d.working_capital = d.cash + d.receivable - d.payable
            d.revenue_ytd = -bal(["income", "income_other"], ytd=True)
            d.expense_ytd = bal(["expense", "expense_depreciation",
                                 "expense_direct_cost"], ytd=True)
            d.net_profit_ytd = d.revenue_ytd - d.expense_ytd
            d.revenue_month = -bal(["income", "income_other"], month=True)

            base = [("company_id", "=", cid), ("state", "=", "posted"),
                    ("payment_state", "in", ("not_paid", "partial"))]
            inv = Move.search(base + [("move_type", "=", "out_invoice")])
            d.unpaid_inv_amount = sum(inv.mapped("amount_residual"))
            d.overdue_amount = sum(inv.filtered(
                lambda m: m.invoice_date_due and m.invoice_date_due < today
            ).mapped("amount_residual"))
            d.unpaid_bill_amount = sum(Move.search(
                base + [("move_type", "=", "in_invoice")]).mapped("amount_residual"))

            tax_lines = AML.search([("company_id", "=", cid),
                                    ("parent_state", "=", "posted"),
                                    ("tax_line_id", "!=", False)])
            d.tax_due = -sum(tax_lines.mapped("balance"))

    # ── Actions ─────────────────────────────────────────────────────────────
    def action_refresh(self):
        return {"type": "ir.actions.act_window", "res_model": "account.overview.board",
                "view_mode": "form", "target": "current"}

    def _open(self, domain, name):
        return {"type": "ir.actions.act_window", "name": name,
                "res_model": "account.move", "domain": domain,
                "view_mode": "list,form", "target": "current"}

    def _cdom(self):
        return [("company_id", "=", self.company_id.id), ("state", "=", "posted")]

    def action_receivable(self):
        return self._open(self._cdom() + [("move_type", "=", "out_invoice"),
                          ("payment_state", "in", ("not_paid", "partial"))],
                          "Open Customer Invoices")

    def action_payable(self):
        return self._open(self._cdom() + [("move_type", "=", "in_invoice"),
                          ("payment_state", "in", ("not_paid", "partial"))],
                          "Open Vendor Bills")

    def action_overdue(self):
        today = fields.Date.context_today(self)
        return self._open(self._cdom() + [
            ("move_type", "=", "out_invoice"),
            ("payment_state", "in", ("not_paid", "partial")),
            ("invoice_date_due", "<", today)], "Overdue Receivables")

    def _ref(self, xmlid):
        act = self.env.ref(xmlid, raise_if_not_found=False)
        return act.sudo().read()[0] if act else {"type": "ir.actions.act_window_close"}

    def action_cashflow(self):
        return self._ref("account_cashflow_lite.action_afr_cashflow")

    def action_loans(self):
        return self._ref("account_loan_lite.action_account_loan_lite")
