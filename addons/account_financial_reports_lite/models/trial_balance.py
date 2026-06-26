from odoo import api, fields, models


class TrialBalance(models.TransientModel):
    _name = "afr.trial.balance"
    _description = "Trial Balance / P&L / Balance Sheet"

    date_from = fields.Date(string="From")
    date_to = fields.Date(string="To", default=fields.Date.context_today)
    target_move = fields.Selection(
        [("posted", "Posted entries"), ("all", "All entries")],
        default="posted", required=True, string="Entries",
    )
    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company, required=True,
    )
    currency_id = fields.Many2one(related="company_id.currency_id")
    line_ids = fields.One2many("afr.trial.balance.line", "report_id", string="Lines")

    # Summary figures (Profit & Loss + Balance Sheet)
    net_profit = fields.Monetary(compute="_compute_summary")
    total_income = fields.Monetary(compute="_compute_summary")
    total_expense = fields.Monetary(compute="_compute_summary")
    total_assets = fields.Monetary(compute="_compute_summary")
    total_liabilities = fields.Monetary(compute="_compute_summary")
    total_equity = fields.Monetary(compute="_compute_summary")

    @api.depends("line_ids")
    def _compute_summary(self):
        for rep in self:
            inc = exp = assets = liab = eq = 0.0
            for ln in rep.line_ids:
                t = ln.account_type or ""
                if t.startswith("income"):
                    inc += ln.balance
                elif t.startswith("expense"):
                    exp += ln.balance
                elif t.startswith("asset"):
                    assets += ln.balance
                elif t.startswith("liability"):
                    liab += ln.balance
                elif t.startswith("equity"):
                    eq += ln.balance
            # Income/liability/equity carry credit (negative) balances → flip sign.
            rep.total_income = -inc
            rep.total_expense = exp
            rep.net_profit = -(inc + exp)
            rep.total_assets = assets
            rep.total_liabilities = -liab
            rep.total_equity = -eq

    def action_compute(self):
        self.ensure_one()
        self.line_ids.unlink()
        domain = [("company_id", "=", self.company_id.id),
                  ("account_id", "!=", False)]
        if self.date_from:
            domain.append(("date", ">=", self.date_from))
        if self.date_to:
            domain.append(("date", "<=", self.date_to))
        if self.target_move == "posted":
            domain.append(("parent_state", "=", "posted"))

        groups = self.env["account.move.line"]._read_group(
            domain, groupby=["account_id"],
            aggregates=["debit:sum", "credit:sum", "balance:sum"],
        )
        Line = self.env["afr.trial.balance.line"]
        for account, debit, credit, balance in groups:
            Line.create({
                "report_id": self.id,
                "account_id": account.id,
                "account_type": account.account_type,
                "debit": debit or 0.0,
                "credit": credit or 0.0,
                "balance": balance or 0.0,
            })
        return {
            "type": "ir.actions.act_window",
            "res_model": "afr.trial.balance",
            "view_mode": "form",
            "res_id": self.id,
            "target": "new",
        }


class TrialBalanceLine(models.TransientModel):
    _name = "afr.trial.balance.line"
    _description = "Trial Balance Line"
    _order = "code"

    report_id = fields.Many2one("afr.trial.balance", ondelete="cascade")
    account_id = fields.Many2one("account.account", string="Account")
    code = fields.Char(related="account_id.code", store=True)
    account_type = fields.Char(string="Type")
    currency_id = fields.Many2one(related="report_id.currency_id")
    debit = fields.Monetary()
    credit = fields.Monetary()
    balance = fields.Monetary()
