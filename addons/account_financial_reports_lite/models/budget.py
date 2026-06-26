from odoo import api, fields, models


class Budget(models.Model):
    _name = "afr.budget"
    _description = "Budget"
    _order = "date_from desc, id desc"

    name = fields.Char(required=True)
    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)
    company_id = fields.Many2one("res.company", default=lambda s: s.env.company)
    currency_id = fields.Many2one(related="company_id.currency_id")
    line_ids = fields.One2many("afr.budget.line", "budget_id", string="Lines")


class BudgetLine(models.Model):
    _name = "afr.budget.line"
    _description = "Budget Line"

    budget_id = fields.Many2one("afr.budget", ondelete="cascade", required=True)
    account_id = fields.Many2one("account.account", string="Account", required=True)
    currency_id = fields.Many2one(related="budget_id.currency_id")
    planned_amount = fields.Monetary(required=True)
    practical_amount = fields.Monetary(compute="_compute_practical", store=False,
                                       string="Actual")
    achievement = fields.Float(compute="_compute_practical", store=False,
                               string="Achieved %")

    @api.depends("account_id", "planned_amount",
                 "budget_id.date_from", "budget_id.date_to")
    def _compute_practical(self):
        for line in self:
            practical = 0.0
            b = line.budget_id
            if line.account_id and b.date_from and b.date_to:
                dom = [
                    ("account_id", "=", line.account_id.id),
                    ("parent_state", "=", "posted"),
                    ("company_id", "=", b.company_id.id),
                    ("date", ">=", b.date_from),
                    ("date", "<=", b.date_to),
                ]
                practical = sum(
                    self.env["account.move.line"].search(dom).mapped("balance"))
                # Income accounts carry credit (negative) balances → show revenue positive.
                if (line.account_id.account_type or "").startswith("income"):
                    practical = -practical
            line.practical_amount = practical
            line.achievement = (practical / line.planned_amount * 100.0
                                if line.planned_amount else 0.0)
