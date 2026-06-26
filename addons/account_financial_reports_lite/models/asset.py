from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


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
        domain=[("account_type", "=", "asset_fixed")])
    depreciation_account_id = fields.Many2one(
        "account.account", string="Depreciation Expense Account",
        domain=[("account_type", "like", "expense")])
    company_id = fields.Many2one("res.company", default=lambda s: s.env.company)
    currency_id = fields.Many2one(related="company_id.currency_id")
    line_ids = fields.One2many("afr.asset.line", "asset_id", string="Depreciation Board")
    depreciated_value = fields.Monetary(compute="_compute_amounts", store=False)
    remaining_value = fields.Monetary(compute="_compute_amounts", store=False)

    @api.depends("line_ids.depreciation_amount", "original_value")
    def _compute_amounts(self):
        for a in self:
            a.depreciated_value = sum(a.line_ids.mapped("depreciation_amount"))
            a.remaining_value = a.original_value - a.depreciated_value

    def action_compute_board(self):
        for a in self:
            a.line_ids.unlink()
            n = a.method_number or 1
            depreciable = a.original_value - a.salvage_value
            per = round(depreciable / n, 2)
            cumulative = 0.0
            vals = []
            for i in range(1, n + 1):
                d = a.acquisition_date + relativedelta(months=int(a.method_period) * i)
                # Last period absorbs the rounding remainder.
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

    def action_set_draft(self):
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
