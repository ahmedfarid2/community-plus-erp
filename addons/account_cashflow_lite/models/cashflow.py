from odoo import api, fields, models


class CashFlow(models.TransientModel):
    _name = "afr.cashflow"
    _description = "Cash Flow Statement"

    date_from = fields.Date(string="From")
    date_to = fields.Date(string="To", default=fields.Date.context_today)
    company_id = fields.Many2one("res.company", default=lambda s: s.env.company,
                                 required=True)
    currency_id = fields.Many2one(related="company_id.currency_id")

    opening_balance = fields.Monetary(compute="_compute_cf")
    operating = fields.Monetary(compute="_compute_cf")
    investing = fields.Monetary(compute="_compute_cf")
    financing = fields.Monetary(compute="_compute_cf")
    net_change = fields.Monetary(compute="_compute_cf")
    closing_balance = fields.Monetary(compute="_compute_cf")

    @api.depends("date_from", "date_to", "company_id")
    def _compute_cf(self):
        AML = self.env["account.move.line"]
        for r in self:
            cash_dom = [("company_id", "=", r.company_id.id),
                        ("parent_state", "=", "posted"),
                        ("account_id.account_type", "=", "asset_cash")]
            # Opening cash = balance of cash accounts strictly before the period.
            opening = 0.0
            if r.date_from:
                opening = sum(AML.search(
                    cash_dom + [("date", "<", r.date_from)]).mapped("balance"))
            r.opening_balance = opening

            period_dom = list(cash_dom)
            if r.date_from:
                period_dom.append(("date", ">=", r.date_from))
            if r.date_to:
                period_dom.append(("date", "<=", r.date_to))
            cash_lines = AML.search(period_dom)

            # Net cash change per journal entry, classified by its counterpart.
            by_move = {}
            for line in cash_lines:
                by_move.setdefault(line.move_id, 0.0)
                by_move[line.move_id] += line.balance

            op = inv = fin = 0.0
            for move, cash_change in by_move.items():
                counter = move.line_ids.filtered(
                    lambda x: x.account_id.account_type != "asset_cash")
                types = set(counter.mapped("account_id.account_type"))
                if any(t in ("asset_fixed", "asset_non_current") for t in types):
                    inv += cash_change
                elif any(t in ("equity", "equity_unaffected") or
                         (t or "").startswith("liability_non_current") for t in types):
                    fin += cash_change
                else:
                    op += cash_change

            r.operating = op
            r.investing = inv
            r.financing = fin
            r.net_change = op + inv + fin
            r.closing_balance = opening + r.net_change

    def action_refresh(self):
        return {"type": "ir.actions.act_window", "res_model": "afr.cashflow",
                "view_mode": "form", "target": "current"}
