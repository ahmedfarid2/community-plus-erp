from odoo import api, fields, models


class MrrLog(models.Model):
    _name = "subscription.lite.mrr.log"
    _description = "MRR History Snapshot"
    _order = "date"
    _rec_name = "date"

    date = fields.Date(required=True, index=True)
    company_id = fields.Many2one("res.company", default=lambda s: s.env.company)
    currency_id = fields.Many2one(related="company_id.currency_id")
    total_mrr = fields.Monetary(string="Total MRR")
    active_count = fields.Integer(string="Active Subscriptions")
    new_mrr = fields.Monetary(string="New MRR")
    churned_mrr = fields.Monetary(string="Churned MRR")
    net_new_mrr = fields.Monetary(string="Net New MRR")
    growth_pct = fields.Float(string="MoM Growth %")

    @api.model
    def _cron_snapshot_mrr(self):
        """Scheduled (monthly): record total/new/churned MRR per company."""
        today = fields.Date.context_today(self)
        Contract = self.env["subscription.lite.contract"]
        created = self.browse()
        for company in self.env["res.company"].search([]):
            active = Contract.search([("state", "=", "active"),
                                      ("company_id", "=", company.id)])
            total = sum(active.mapped("mrr"))
            prev = self.search([("company_id", "=", company.id)],
                               order="date desc", limit=1)
            new_mrr = churned = 0.0
            if prev:
                new = Contract.search([("company_id", "=", company.id),
                                       ("activated_date", ">", prev.date),
                                       ("activated_date", "<=", today)])
                new_mrr = sum(new.mapped("mrr"))
                ch = Contract.search([("company_id", "=", company.id),
                                      ("churned_date", ">", prev.date),
                                      ("churned_date", "<=", today)])
                churned = sum(ch.mapped("mrr"))
            growth = ((total - prev.total_mrr) / prev.total_mrr * 100.0) \
                if (prev and prev.total_mrr) else 0.0
            created |= self.create({
                "date": today, "company_id": company.id,
                "total_mrr": total, "active_count": len(active),
                "new_mrr": new_mrr, "churned_mrr": churned,
                "net_new_mrr": new_mrr - churned, "growth_pct": growth,
            })
        return len(created)
