from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import UserError


class Deferred(models.Model):
    _name = "account.deferred.lite"
    _description = "Deferred Revenue / Expense"
    _order = "start_date desc, id desc"

    name = fields.Char(required=True)
    deferred_type = fields.Selection(
        [("revenue", "Deferred Revenue"), ("expense", "Deferred Expense")],
        default="revenue", required=True)
    state = fields.Selection(
        [("draft", "Draft"), ("running", "Running"), ("closed", "Closed")],
        default="draft", required=True)
    total_amount = fields.Monetary(required=True)
    start_date = fields.Date(default=fields.Date.context_today, required=True)
    number = fields.Integer("Number of Periods", default=12, required=True)
    period_months = fields.Selection(
        [("1", "Months"), ("12", "Years")], default="1", required=True,
        string="Period Length")
    recognition_account_id = fields.Many2one(
        "account.account", string="Recognition Account (P&L)",
        help="Income account (revenue) or expense account (expense).")
    deferred_account_id = fields.Many2one(
        "account.account", string="Deferred Account (Balance Sheet)",
        help="Unearned-revenue liability (revenue) or prepaid asset (expense).")
    journal_id = fields.Many2one(
        "account.journal", domain=[("type", "=", "general")],
        default=lambda s: s._def_journal())
    company_id = fields.Many2one("res.company", default=lambda s: s.env.company)
    currency_id = fields.Many2one(related="company_id.currency_id")
    line_ids = fields.One2many("account.deferred.lite.line", "deferred_id",
                               string="Recognition Schedule")
    recognized_amount = fields.Monetary(compute="_compute_amounts", store=False)
    residual_amount = fields.Monetary(compute="_compute_amounts", store=False)

    def _def_journal(self):
        return self.env["account.journal"].search(
            [("type", "=", "general"), ("company_id", "=", self.env.company.id)], limit=1)

    @api.depends("line_ids.amount", "line_ids.move_id", "total_amount")
    def _compute_amounts(self):
        for r in self:
            rec = sum(r.line_ids.filtered("move_id").mapped("amount"))
            r.recognized_amount = rec
            r.residual_amount = r.total_amount - rec

    def action_compute_board(self):
        for r in self:
            r.line_ids.filtered(lambda l: not l.move_id).unlink()
            if r.line_ids:
                raise UserError("Posted recognition lines already exist.")
            n = r.number or 1
            per = round(r.total_amount / n, 2)
            cum = 0.0
            vals = []
            for i in range(1, n + 1):
                d = r.start_date + relativedelta(months=int(r.period_months) * i)
                amt = per if i < n else round(r.total_amount - per * (n - 1), 2)
                cum += amt
                vals.append({"deferred_id": r.id, "sequence": i, "date": d,
                             "amount": amt, "cumulative": cum,
                             "residual": r.total_amount - cum})
            self.env["account.deferred.lite.line"].create(vals)
            r.state = "running"
        return True

    def action_recognize(self):
        """Post a recognition entry for each due, not-yet-posted period."""
        today = fields.Date.context_today(self)
        Move = self.env["account.move"]
        for r in self:
            if not r.recognition_account_id or not r.deferred_account_id:
                raise UserError("Set the Recognition and Deferred accounts first.")
            journal = r.journal_id or r._def_journal()
            for line in r.line_ids:
                if line.move_id or (line.date and line.date > today):
                    continue
                ref = "%s %s #%s" % (
                    dict(r._fields["deferred_type"].selection)[r.deferred_type],
                    r.name, line.sequence)
                if r.deferred_type == "revenue":
                    debit, credit = r.deferred_account_id, r.recognition_account_id
                else:
                    debit, credit = r.recognition_account_id, r.deferred_account_id
                move = Move.create({
                    "move_type": "entry", "journal_id": journal.id,
                    "date": line.date, "ref": ref,
                    "line_ids": [
                        (0, 0, {"name": ref, "account_id": debit.id,
                                "debit": line.amount, "credit": 0.0}),
                        (0, 0, {"name": ref, "account_id": credit.id,
                                "debit": 0.0, "credit": line.amount}),
                    ]})
                move.action_post()
                line.move_id = move.id
        return True

    def action_set_draft(self):
        if self.mapped("line_ids").filtered("move_id"):
            raise UserError("Cannot reset: posted recognition entries exist.")
        self.write({"state": "draft"})
        self.mapped("line_ids").unlink()

    def action_close(self):
        self.write({"state": "closed"})


class DeferredLine(models.Model):
    _name = "account.deferred.lite.line"
    _description = "Deferred Recognition Line"
    _order = "sequence"

    deferred_id = fields.Many2one("account.deferred.lite", ondelete="cascade",
                                  required=True)
    sequence = fields.Integer()
    date = fields.Date(string="Recognition Date")
    currency_id = fields.Many2one(related="deferred_id.currency_id")
    amount = fields.Monetary()
    cumulative = fields.Monetary()
    residual = fields.Monetary()
    move_id = fields.Many2one("account.move", string="Journal Entry", readonly=True)
    posted = fields.Boolean(compute="_compute_posted", store=False)

    @api.depends("move_id", "move_id.state")
    def _compute_posted(self):
        for line in self:
            line.posted = bool(line.move_id) and line.move_id.state == "posted"
