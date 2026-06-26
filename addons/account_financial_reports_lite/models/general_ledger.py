from odoo import fields, models


class GeneralLedger(models.TransientModel):
    _name = "afr.general.ledger"
    _description = "General Ledger"

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
    line_ids = fields.One2many("afr.general.ledger.line", "report_id", string="Lines")

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

        moves = self.env["account.move.line"].search(
            domain, order="account_id, date, id")
        running = {}
        vals = []
        for ml in moves:
            running[ml.account_id.id] = running.get(ml.account_id.id, 0.0) + ml.balance
            vals.append({
                "report_id": self.id,
                "account_id": ml.account_id.id,
                "move_name": ml.move_id.name,
                "date": ml.date,
                "label": ml.name or "",
                "partner_id": ml.partner_id.id,
                "debit": ml.debit,
                "credit": ml.credit,
                "balance_running": running[ml.account_id.id],
            })
        self.env["afr.general.ledger.line"].create(vals)
        return {
            "type": "ir.actions.act_window",
            "res_model": "afr.general.ledger",
            "view_mode": "form",
            "res_id": self.id,
            "target": "new",
        }


class GeneralLedgerLine(models.TransientModel):
    _name = "afr.general.ledger.line"
    _description = "General Ledger Line"
    _order = "account_id, date, id"

    report_id = fields.Many2one("afr.general.ledger", ondelete="cascade")
    account_id = fields.Many2one("account.account", string="Account")
    move_name = fields.Char(string="Entry")
    date = fields.Date()
    label = fields.Char(string="Label")
    partner_id = fields.Many2one("res.partner", string="Partner")
    currency_id = fields.Many2one(related="report_id.currency_id")
    debit = fields.Monetary()
    credit = fields.Monetary()
    balance_running = fields.Monetary(string="Cumulative Balance")
