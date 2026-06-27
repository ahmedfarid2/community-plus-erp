from odoo import api, fields, models


class Dashboard(models.TransientModel):
    _name = "dashboards.lite.board"
    _description = "Company Dashboard"

    company_id = fields.Many2one("res.company", default=lambda s: s.env.company)
    currency_id = fields.Many2one(related="company_id.currency_id")

    # Finance
    cash = fields.Monetary(compute="_compute_kpis")
    receivable = fields.Monetary(compute="_compute_kpis")
    payable = fields.Monetary(compute="_compute_kpis")
    net_profit_ytd = fields.Monetary(compute="_compute_kpis")
    unpaid_invoices = fields.Monetary(compute="_compute_kpis")
    # Sales
    mrr = fields.Monetary(compute="_compute_kpis")
    open_quotations = fields.Integer(compute="_compute_kpis")
    # Operations
    open_tickets = fields.Integer(compute="_compute_kpis")
    pending_approvals = fields.Integer(compute="_compute_kpis")
    expiring_docs = fields.Integer(compute="_compute_kpis")
    todays_bookings = fields.Integer(compute="_compute_kpis")
    employees = fields.Integer(compute="_compute_kpis")

    def _count(self, model, domain):
        return self.env[model].search_count(domain) if model in self.env else 0

    @api.depends("company_id")
    def _compute_kpis(self):
        today = fields.Date.context_today(self)
        for d in self:
            cid = d.company_id.id
            AML = self.env["account.move.line"]

            def bal(types, ytd=False):
                dom = [("company_id", "=", cid), ("parent_state", "=", "posted"),
                       ("account_id.account_type", "in", types)]
                if ytd:
                    dom.append(("date", ">=", today.replace(month=1, day=1)))
                return sum(AML.search(dom).mapped("balance"))

            d.cash = bal(["asset_cash"])
            d.receivable = bal(["asset_receivable"])
            d.payable = -bal(["liability_payable"])
            rev = -bal(["income", "income_other"], ytd=True)
            exp = bal(["expense", "expense_depreciation", "expense_direct_cost"], ytd=True)
            d.net_profit_ytd = rev - exp
            inv = self.env["account.move"].search([
                ("company_id", "=", cid), ("move_type", "=", "out_invoice"),
                ("state", "=", "posted"), ("payment_state", "in", ("not_paid", "partial"))])
            d.unpaid_invoices = sum(inv.mapped("amount_residual"))

            d.open_quotations = self._count(
                "sale.order", [("company_id", "=", cid), ("state", "in", ("draft", "sent"))])
            d.mrr = 0.0
            if "subscription.lite.contract" in self.env:
                d.mrr = sum(self.env["subscription.lite.contract"].search(
                    [("company_id", "=", cid), ("state", "=", "active")]).mapped("mrr"))

            d.open_tickets = self._count(
                "helpdesk.lite.ticket",
                [("company_id", "=", cid), ("state", "not in", ("solved", "cancelled"))])
            d.pending_approvals = self._count(
                "business.approval.request",
                [("company_id", "=", cid), ("state", "=", "submitted")])
            d.expiring_docs = self._count(
                "documents.lite.document",
                [("company_id", "=", cid), ("expiry_state", "in", ("expiring", "expired"))])
            d.employees = self._count("hr.employee", [("company_id", "=", cid)])
            d.todays_bookings = self._count(
                "meeting.lite.booking",
                [("company_id", "=", cid),
                 ("start_datetime", ">=", "%s 00:00:00" % today),
                 ("start_datetime", "<=", "%s 23:59:59" % today)])

    def action_refresh(self):
        return {"type": "ir.actions.act_window", "res_model": "dashboards.lite.board",
                "view_mode": "form", "target": "current"}
