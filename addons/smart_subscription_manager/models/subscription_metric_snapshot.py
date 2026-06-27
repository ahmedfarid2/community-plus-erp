from odoo import api, fields, models


class SubscriptionMetricSnapshot(models.Model):
    _name = "subscription.metric.snapshot"
    _description = "Subscription Metric Snapshot"
    _order = "snapshot_date desc, id desc"

    snapshot_date = fields.Date(default=fields.Date.context_today, required=True)
    company_id = fields.Many2one(
        "res.company", default=lambda s: s.env.company)
    currency_id = fields.Many2one(related="company_id.currency_id")

    active_subscriptions_count = fields.Integer()
    trial_subscriptions_count = fields.Integer()
    paused_subscriptions_count = fields.Integer()
    cancelled_subscriptions_count = fields.Integer()
    expired_subscriptions_count = fields.Integer()

    mrr = fields.Monetary(currency_field="currency_id", string="MRR")
    arr = fields.Monetary(currency_field="currency_id", string="ARR")
    new_mrr = fields.Monetary(currency_field="currency_id")
    expansion_mrr = fields.Monetary(currency_field="currency_id")
    contraction_mrr = fields.Monetary(currency_field="currency_id")
    churned_mrr = fields.Monetary(currency_field="currency_id")
    net_mrr = fields.Monetary(currency_field="currency_id")
    churn_rate = fields.Float(string="Churn Rate (%)")
    notes = fields.Text()

    @api.model
    def generate_snapshot(self, company=None):
        """Capture current subscription metrics for the company."""
        company = company or self.env.company
        Sub = self.env["subscription.subscription"]
        base = [("company_id", "=", company.id)]

        def count(state):
            return Sub.search_count(base + [("state", "=", state)])

        active = Sub.search(base + [("state", "in", ("active", "trial"))])
        mrr = sum(active.mapped("mrr_amount"))
        cancelled = count("cancelled")
        active_n = len(active)
        churn_rate = (cancelled / (active_n + cancelled) * 100.0) \
            if (active_n + cancelled) else 0.0

        prev = self.search(base, order="snapshot_date desc", limit=1)
        net = mrr - (prev.mrr if prev else 0.0)

        return self.create({
            "snapshot_date": fields.Date.context_today(self),
            "company_id": company.id,
            "active_subscriptions_count": count("active"),
            "trial_subscriptions_count": count("trial"),
            "paused_subscriptions_count": count("paused"),
            "cancelled_subscriptions_count": cancelled,
            "expired_subscriptions_count": count("expired"),
            "mrr": mrr,
            "arr": mrr * 12.0,
            "new_mrr": max(net, 0.0),
            "contraction_mrr": -min(net, 0.0),
            "net_mrr": net,
            "churn_rate": churn_rate,
        })
