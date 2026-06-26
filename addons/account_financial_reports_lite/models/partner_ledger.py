from odoo import fields, models


class PartnerLedger(models.TransientModel):
    _name = "afr.partner.ledger"
    _description = "Partner Ledger"

    date_from = fields.Date(string="From")
    date_to = fields.Date(string="To", default=fields.Date.context_today)
    target_move = fields.Selection(
        [("posted", "Posted entries"), ("all", "All entries")],
        default="posted", required=True, string="Entries")
    account_filter = fields.Selection(
        [("all", "Receivable + Payable"),
         ("asset_receivable", "Receivable only"),
         ("liability_payable", "Payable only")],
        default="all", required=True, string="Accounts")
    company_id = fields.Many2one("res.company", default=lambda s: s.env.company,
                                 required=True)
    currency_id = fields.Many2one(related="company_id.currency_id")
    line_ids = fields.One2many("afr.partner.ledger.line", "report_id", string="Lines")

    def action_compute(self):
        self.ensure_one()
        self.line_ids.unlink()
        dom = [("company_id", "=", self.company_id.id),
               ("partner_id", "!=", False),
               ("account_id", "!=", False)]
        if self.date_from:
            dom.append(("date", ">=", self.date_from))
        if self.date_to:
            dom.append(("date", "<=", self.date_to))
        if self.target_move == "posted":
            dom.append(("parent_state", "=", "posted"))
        if self.account_filter == "all":
            dom.append(("account_id.account_type", "in",
                        ("asset_receivable", "liability_payable")))
        else:
            dom.append(("account_id.account_type", "=", self.account_filter))

        moves = self.env["account.move.line"].search(
            dom, order="partner_id, date, id")
        running = {}
        vals = []
        for ml in moves:
            running[ml.partner_id.id] = running.get(ml.partner_id.id, 0.0) + ml.balance
            vals.append({
                "report_id": self.id,
                "partner_id": ml.partner_id.id,
                "date": ml.date,
                "move_name": ml.move_id.name,
                "account_id": ml.account_id.id,
                "debit": ml.debit,
                "credit": ml.credit,
                "balance_running": running[ml.partner_id.id],
            })
        self.env["afr.partner.ledger.line"].create(vals)
        return {
            "type": "ir.actions.act_window",
            "res_model": "afr.partner.ledger",
            "view_mode": "form",
            "res_id": self.id,
            "target": "new",
        }


class PartnerLedgerLine(models.TransientModel):
    _name = "afr.partner.ledger.line"
    _description = "Partner Ledger Line"
    _order = "partner_id, date, id"

    report_id = fields.Many2one("afr.partner.ledger", ondelete="cascade")
    partner_id = fields.Many2one("res.partner", string="Partner")
    date = fields.Date()
    move_name = fields.Char(string="Entry")
    account_id = fields.Many2one("account.account", string="Account")
    currency_id = fields.Many2one(related="report_id.currency_id")
    debit = fields.Monetary()
    credit = fields.Monetary()
    balance_running = fields.Monetary(string="Cumulative Balance")
