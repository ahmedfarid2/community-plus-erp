from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class Loan(models.Model):
    _name = "account.loan.lite"
    _description = "Loan"
    _order = "start_date desc, id desc"

    name = fields.Char(required=True)
    state = fields.Selection(
        [("draft", "Draft"), ("running", "Running"), ("closed", "Closed")],
        default="draft", required=True)
    principal = fields.Monetary(string="Amount Borrowed", required=True)
    interest_rate = fields.Float(string="Annual Interest %", default=10.0)
    start_date = fields.Date(default=fields.Date.context_today, required=True)
    term_number = fields.Integer("Number of Installments", default=12, required=True)
    term_period = fields.Selection(
        [("1", "Months"), ("12", "Years")], default="1", required=True,
        string="Installment Every")
    company_id = fields.Many2one("res.company", default=lambda s: s.env.company)
    currency_id = fields.Many2one(related="company_id.currency_id")
    line_ids = fields.One2many("account.loan.lite.line", "loan_id",
                               string="Amortization Schedule")
    total_interest = fields.Monetary(compute="_compute_totals", store=False)
    total_payment = fields.Monetary(compute="_compute_totals", store=False)

    @api.depends("line_ids.interest_amount", "line_ids.payment_amount")
    def _compute_totals(self):
        for loan in self:
            loan.total_interest = sum(loan.line_ids.mapped("interest_amount"))
            loan.total_payment = sum(loan.line_ids.mapped("payment_amount"))

    def action_compute_schedule(self):
        for loan in self:
            loan.line_ids.unlink()
            n = loan.term_number or 1
            months = int(loan.term_period)
            principal_per = round(loan.principal / n, 2)
            rate_per_period = (loan.interest_rate / 100.0) * (months / 12.0)
            remaining = loan.principal
            vals = []
            for i in range(1, n + 1):
                d = loan.start_date + relativedelta(months=months * i)
                interest = round(remaining * rate_per_period, 2)
                # Last installment clears any rounding remainder of principal.
                principal_amt = principal_per if i < n else round(remaining, 2)
                remaining = round(remaining - principal_amt, 2)
                vals.append({
                    "loan_id": loan.id, "sequence": i, "date": d,
                    "principal_amount": principal_amt,
                    "interest_amount": interest,
                    "payment_amount": round(principal_amt + interest, 2),
                    "remaining_balance": remaining,
                })
            self.env["account.loan.lite.line"].create(vals)
            loan.state = "running"
        return True

    def action_set_draft(self):
        self.write({"state": "draft"})
        self.mapped("line_ids").unlink()

    def action_close(self):
        self.write({"state": "closed"})


class LoanLine(models.Model):
    _name = "account.loan.lite.line"
    _description = "Loan Amortization Line"
    _order = "sequence"

    loan_id = fields.Many2one("account.loan.lite", ondelete="cascade", required=True)
    sequence = fields.Integer()
    date = fields.Date(string="Due Date")
    currency_id = fields.Many2one(related="loan_id.currency_id")
    principal_amount = fields.Monetary(string="Principal")
    interest_amount = fields.Monetary(string="Interest")
    payment_amount = fields.Monetary(string="Installment")
    remaining_balance = fields.Monetary(string="Balance")
