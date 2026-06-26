from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import UserError


class Asset(models.Model):
    _name = "afr.asset"
    _description = "Fixed Asset"
    _order = "acquisition_date desc, id desc"

    name = fields.Char(required=True)
    state = fields.Selection(
        [("draft", "Draft"), ("open", "Running"), ("close", "Closed")],
        default="draft", required=True)
    original_value = fields.Monetary(required=True)
    salvage_value = fields.Monetary(help="Residual value not depreciated.")
    acquisition_date = fields.Date(default=fields.Date.context_today, required=True)
    method_number = fields.Integer("Number of Depreciations", default=5, required=True)
    method_period = fields.Selection(
        [("12", "Years"), ("1", "Months")], default="12", required=True,
        string="Period Length")
    asset_account_id = fields.Many2one(
        "account.account", string="Fixed Asset Account",
        default=lambda s: s._default_account("asset_fixed"),
        domain=[("account_type", "=", "asset_fixed")])
    depreciation_account_id = fields.Many2one(
        "account.account", string="Depreciation Expense Account",
        default=lambda s: s._default_account("expense"),
        domain=[("account_type", "like", "expense")])
    journal_id = fields.Many2one(
        "account.journal", string="Depreciation Journal",
        default=lambda s: s._default_journal(),
        domain=[("type", "=", "general")])
    company_id = fields.Many2one("res.company", default=lambda s: s.env.company)
    currency_id = fields.Many2one(related="company_id.currency_id")
    line_ids = fields.One2many("afr.asset.line", "asset_id", string="Depreciation Board")
    depreciated_value = fields.Monetary(compute="_compute_amounts", store=False)
    remaining_value = fields.Monetary(compute="_compute_amounts", store=False)
    posted_count = fields.Integer(compute="_compute_amounts", store=False)

    def _default_account(self, like):
        op = "=" if like == "asset_fixed" else "like"
        return self.env["account.account"].search([("account_type", op, like)], limit=1)

    def _default_journal(self):
        return self.env["account.journal"].search(
            [("type", "=", "general"), ("company_id", "=", self.env.company.id)], limit=1)

    @api.depends("line_ids.depreciation_amount", "line_ids.move_id", "original_value")
    def _compute_amounts(self):
        for a in self:
            a.depreciated_value = sum(a.line_ids.mapped("depreciation_amount"))
            a.remaining_value = a.original_value - a.depreciated_value
            a.posted_count = len(a.line_ids.filtered("move_id"))

    def action_compute_board(self):
        for a in self:
            a.line_ids.filtered(lambda l: not l.move_id).unlink()
            if a.line_ids:
                raise UserError("Some depreciation lines are already posted; "
                                "reset to draft is blocked once entries exist.")
            n = a.method_number or 1
            depreciable = a.original_value - a.salvage_value
            per = round(depreciable / n, 2)
            cumulative = 0.0
            vals = []
            for i in range(1, n + 1):
                d = a.acquisition_date + relativedelta(months=int(a.method_period) * i)
                amount = per if i < n else round(depreciable - per * (n - 1), 2)
                cumulative += amount
                vals.append({
                    "asset_id": a.id, "sequence": i, "date": d,
                    "depreciation_amount": amount,
                    "cumulative_depreciation": cumulative,
                    "remaining_value": a.original_value - cumulative,
                })
            self.env["afr.asset.line"].create(vals)
            a.state = "open"
        return True

    def action_post_depreciation(self):
        """Create + post a journal entry for every due, not-yet-posted line."""
        today = fields.Date.context_today(self)
        Move = self.env["account.move"]
        for a in self:
            if not a.depreciation_account_id or not a.asset_account_id:
                raise UserError("Set the Fixed Asset Account and the Depreciation "
                                "Expense Account on the asset first.")
            journal = a.journal_id or a._default_journal()
            if not journal:
                raise UserError("No Miscellaneous (general) journal found.")
            for line in a.line_ids:
                if line.move_id or (line.date and line.date > today):
                    continue
                ref = "Depreciation %s #%s" % (a.name, line.sequence)
                move = Move.create({
                    "move_type": "entry",
                    "journal_id": journal.id,
                    "date": line.date,
                    "ref": ref,
                    "line_ids": [
                        (0, 0, {"name": ref,
                                "account_id": a.depreciation_account_id.id,
                                "debit": line.depreciation_amount, "credit": 0.0}),
                        (0, 0, {"name": ref,
                                "account_id": a.asset_account_id.id,
                                "debit": 0.0, "credit": line.depreciation_amount}),
                    ],
                })
                move.action_post()
                line.move_id = move.id
        return True

    def action_set_draft(self):
        if self.mapped("line_ids").filtered("move_id"):
            raise UserError("Cannot reset: posted depreciation entries exist.")
        self.write({"state": "draft"})
        self.mapped("line_ids").unlink()

    def action_close(self):
        self.write({"state": "close"})


class AssetLine(models.Model):
    _name = "afr.asset.line"
    _description = "Depreciation Board Line"
    _order = "sequence"

    asset_id = fields.Many2one("afr.asset", ondelete="cascade", required=True)
    sequence = fields.Integer()
    date = fields.Date(string="Depreciation Date")
    currency_id = fields.Many2one(related="asset_id.currency_id")
    depreciation_amount = fields.Monetary()
    cumulative_depreciation = fields.Monetary()
    remaining_value = fields.Monetary()
    move_id = fields.Many2one("account.move", string="Journal Entry", readonly=True)
    posted = fields.Boolean(compute="_compute_posted", store=False)

    @api.depends("move_id", "move_id.state")
    def _compute_posted(self):
        for line in self:
            line.posted = bool(line.move_id) and line.move_id.state == "posted"
