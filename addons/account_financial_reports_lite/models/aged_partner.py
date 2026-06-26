from odoo import fields, models


class AgedPartner(models.TransientModel):
    _name = "afr.aged.partner"
    _description = "Aged Receivable / Payable"

    as_of_date = fields.Date(string="As of", default=fields.Date.context_today,
                             required=True)
    account_type = fields.Selection(
        [("asset_receivable", "Receivable (customers owe us)"),
         ("liability_payable", "Payable (we owe vendors)")],
        default="asset_receivable", required=True, string="Report",
    )
    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company, required=True,
    )
    currency_id = fields.Many2one(related="company_id.currency_id")
    line_ids = fields.One2many("afr.aged.partner.line", "report_id", string="Lines")

    def action_compute(self):
        self.ensure_one()
        self.line_ids.unlink()
        domain = [
            ("company_id", "=", self.company_id.id),
            ("parent_state", "=", "posted"),
            ("account_id.account_type", "=", self.account_type),
            ("amount_residual", "!=", 0.0),
            ("date", "<=", self.as_of_date),
        ]
        moves = self.env["account.move.line"].search(domain)
        # buckets: [not_due, 1-30, 31-60, 61-90, 91-120, >120]
        agg = {}
        for ml in moves:
            due = ml.date_maturity or ml.date
            age = (self.as_of_date - due).days
            amt = ml.amount_residual
            b = agg.setdefault(ml.partner_id.id, [0.0] * 6)
            if age <= 0:
                b[0] += amt
            elif age <= 30:
                b[1] += amt
            elif age <= 60:
                b[2] += amt
            elif age <= 90:
                b[3] += amt
            elif age <= 120:
                b[4] += amt
            else:
                b[5] += amt
        Line = self.env["afr.aged.partner.line"]
        vals = []
        for partner_id, b in agg.items():
            vals.append({
                "report_id": self.id,
                "partner_id": partner_id,
                "not_due": b[0], "b_1_30": b[1], "b_31_60": b[2],
                "b_61_90": b[3], "b_91_120": b[4], "b_over_120": b[5],
                "total": sum(b),
            })
        Line.create(vals)
        return {
            "type": "ir.actions.act_window",
            "res_model": "afr.aged.partner",
            "view_mode": "form",
            "res_id": self.id,
            "target": "new",
        }


class AgedPartnerLine(models.TransientModel):
    _name = "afr.aged.partner.line"
    _description = "Aged Partner Line"
    _order = "total desc"

    report_id = fields.Many2one("afr.aged.partner", ondelete="cascade")
    partner_id = fields.Many2one("res.partner", string="Partner")
    currency_id = fields.Many2one(related="report_id.currency_id")
    not_due = fields.Monetary(string="Not Due")
    b_1_30 = fields.Monetary(string="1-30")
    b_31_60 = fields.Monetary(string="31-60")
    b_61_90 = fields.Monetary(string="61-90")
    b_91_120 = fields.Monetary(string="91-120")
    b_over_120 = fields.Monetary(string="120+")
    total = fields.Monetary(string="Total")
