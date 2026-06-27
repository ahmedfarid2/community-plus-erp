from odoo import api, fields, models


class SubscriptionBoard(models.TransientModel):
    _name = "subscription.lite.board"
    _description = "Subscriptions Dashboard"

    company_id = fields.Many2one("res.company", default=lambda s: s.env.company)
    currency_id = fields.Many2one(related="company_id.currency_id")

    mrr = fields.Monetary(compute="_compute_kpis")
    arr = fields.Monetary(compute="_compute_kpis")
    active_count = fields.Integer(compute="_compute_kpis")
    draft = fields.Integer(compute="_compute_kpis")
    paused = fields.Integer(compute="_compute_kpis")
    churned = fields.Integer(compute="_compute_kpis")
    arpu = fields.Monetary(compute="_compute_kpis")
    due_invoicing = fields.Integer(compute="_compute_kpis")

    @api.depends("company_id")
    def _compute_kpis(self):
        C = self.env["subscription.lite.contract"]
        for b in self:
            cdom = [("company_id", "=", b.company_id.id)]
            act = C.search(cdom + [("state", "=", "active")])
            b.active_count = len(act)
            b.draft = C.search_count(cdom + [("state", "=", "draft")])
            b.paused = C.search_count(cdom + [("state", "=", "paused")])
            b.churned = C.search_count(cdom + [("state", "=", "closed")])
            b.mrr = sum(act.mapped("mrr"))
            b.arr = b.mrr * 12
            b.arpu = (b.mrr / b.active_count) if b.active_count else 0.0
            today = fields.Date.context_today(self)
            b.due_invoicing = C.search_count(
                cdom + [("state", "=", "active"), ("next_invoice_date", "<=", today)])

    def _open(self, extra, name):
        return {"type": "ir.actions.act_window", "name": name,
                "res_model": "subscription.lite.contract",
                "domain": [("company_id", "=", self.company_id.id)] + extra,
                "view_mode": "list,form", "target": "current"}

    def action_active(self):
        return self._open([("state", "=", "active")], "Active Subscriptions")

    def action_draft(self):
        return self._open([("state", "=", "draft")], "Draft Subscriptions")

    def action_churned(self):
        return self._open([("state", "=", "closed")], "Churned Subscriptions")

    def action_due(self):
        return self._open(
            [("state", "=", "active"),
             ("next_invoice_date", "<=", fields.Date.context_today(self))],
            "Due for Invoicing")

    def action_mrr_log(self):
        return {"type": "ir.actions.act_window", "name": "MRR Evolution",
                "res_model": "subscription.lite.mrr.log",
                "view_mode": "graph,pivot,list", "target": "current"}

    def action_refresh(self):
        return {"type": "ir.actions.act_window",
                "res_model": "subscription.lite.board",
                "view_mode": "form", "target": "current"}
