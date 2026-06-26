from odoo import fields, models


class TaxReport(models.TransientModel):
    _name = "afr.tax.report"
    _description = "Tax Report (collected vs. paid)"

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
    line_ids = fields.One2many("afr.tax.report.line", "report_id", string="Lines")

    tax_collected = fields.Monetary(compute="_compute_summary")  # on sales
    tax_paid = fields.Monetary(compute="_compute_summary")       # on purchases
    tax_net_due = fields.Monetary(compute="_compute_summary")    # to pay authority

    def _compute_summary(self):
        for rep in self:
            coll = sum(l.tax_amount for l in rep.line_ids if l.type_tax_use == "sale")
            paid = sum(l.tax_amount for l in rep.line_ids if l.type_tax_use == "purchase")
            rep.tax_collected = coll
            rep.tax_paid = paid
            rep.tax_net_due = coll - paid

    def _base_domain(self):
        dom = [("company_id", "=", self.company_id.id)]
        if self.date_from:
            dom.append(("date", ">=", self.date_from))
        if self.date_to:
            dom.append(("date", "<=", self.date_to))
        if self.target_move == "posted":
            dom.append(("parent_state", "=", "posted"))
        return dom

    def action_compute(self):
        self.ensure_one()
        self.line_ids.unlink()
        AML = self.env["account.move.line"]
        taxes = self.env["account.tax"].search(
            [("company_id", "=", self.company_id.id),
             ("type_tax_use", "in", ("sale", "purchase"))])
        Line = self.env["afr.tax.report.line"]
        for tax in taxes:
            # Tax amount = lines that ARE this tax; base = lines taxed BY this tax.
            tax_amt = sum(AML.search(
                self._base_domain() + [("tax_line_id", "=", tax.id)]).mapped("balance"))
            base_amt = sum(AML.search(
                self._base_domain() + [("tax_ids", "in", tax.id)]).mapped("balance"))
            if not tax_amt and not base_amt:
                continue
            # Sales carry credit (negative) balances → flip so figures read positive.
            sign = -1.0 if tax.type_tax_use == "sale" else 1.0
            Line.create({
                "report_id": self.id,
                "tax_id": tax.id,
                "type_tax_use": tax.type_tax_use,
                "net_base": base_amt * sign,
                "tax_amount": tax_amt * sign,
            })
        return {
            "type": "ir.actions.act_window",
            "res_model": "afr.tax.report",
            "view_mode": "form",
            "res_id": self.id,
            "target": "new",
        }


class TaxReportLine(models.TransientModel):
    _name = "afr.tax.report.line"
    _description = "Tax Report Line"
    _order = "type_tax_use, tax_id"

    report_id = fields.Many2one("afr.tax.report", ondelete="cascade")
    tax_id = fields.Many2one("account.tax", string="Tax")
    type_tax_use = fields.Selection(
        [("sale", "Sales"), ("purchase", "Purchases")], string="Type")
    currency_id = fields.Many2one(related="report_id.currency_id")
    net_base = fields.Monetary(string="Net Base")
    tax_amount = fields.Monetary(string="Tax")
