from odoo import fields, models, tools


class PaymentPlanAging(models.Model):
    _name = "payment.plan.aging"
    _description = "Payment Plan Aging Analysis"
    _auto = False
    _rec_name = "partner_id"
    _order = "due_date"

    line_id = fields.Many2one("payment.plan.line", string="Payment Line",
                              readonly=True)
    plan_id = fields.Many2one("payment.plan", string="Payment Plan",
                              readonly=True)
    partner_id = fields.Many2one("res.partner", string="Customer", readonly=True)
    responsible_user_id = fields.Many2one("res.users", string="Responsible",
                                          readonly=True)
    company_id = fields.Many2one("res.company", string="Company", readonly=True)
    currency_id = fields.Many2one("res.currency", string="Currency",
                                  readonly=True)
    due_date = fields.Date(string="Due Date", readonly=True)
    days_overdue = fields.Integer(string="Days Overdue", readonly=True)
    remaining_amount = fields.Monetary(
        string="Remaining", currency_field="currency_id", readonly=True)

    # Bucketed remaining amounts (each row populates exactly one bucket).
    current_amount = fields.Monetary(
        string="Not Due", currency_field="currency_id", readonly=True)
    b_1_30 = fields.Monetary(
        string="1-30", currency_field="currency_id", readonly=True)
    b_31_60 = fields.Monetary(
        string="31-60", currency_field="currency_id", readonly=True)
    b_61_90 = fields.Monetary(
        string="61-90", currency_field="currency_id", readonly=True)
    b_90_plus = fields.Monetary(
        string="90+", currency_field="currency_id", readonly=True)
    bucket = fields.Selection(
        [("current", "Not Due"),
         ("b1_30", "1-30 days"),
         ("b31_60", "31-60 days"),
         ("b61_90", "61-90 days"),
         ("b90_plus", "90+ days")],
        string="Aging Bucket", readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    l.id                              AS id,
                    l.id                              AS line_id,
                    l.plan_id                         AS plan_id,
                    l.partner_id                      AS partner_id,
                    l.responsible_user_id             AS responsible_user_id,
                    l.company_id                      AS company_id,
                    l.currency_id                     AS currency_id,
                    l.due_date                        AS due_date,
                    CASE WHEN l.due_date < CURRENT_DATE
                         THEN (CURRENT_DATE - l.due_date) ELSE 0 END
                                                      AS days_overdue,
                    l.remaining_amount                AS remaining_amount,
                    CASE WHEN l.due_date IS NULL OR l.due_date >= CURRENT_DATE
                         THEN l.remaining_amount ELSE 0 END        AS current_amount,
                    CASE WHEN CURRENT_DATE - l.due_date BETWEEN 1 AND 30
                         THEN l.remaining_amount ELSE 0 END        AS b_1_30,
                    CASE WHEN CURRENT_DATE - l.due_date BETWEEN 31 AND 60
                         THEN l.remaining_amount ELSE 0 END        AS b_31_60,
                    CASE WHEN CURRENT_DATE - l.due_date BETWEEN 61 AND 90
                         THEN l.remaining_amount ELSE 0 END        AS b_61_90,
                    CASE WHEN CURRENT_DATE - l.due_date > 90
                         THEN l.remaining_amount ELSE 0 END        AS b_90_plus,
                    CASE
                         WHEN l.due_date IS NULL OR l.due_date >= CURRENT_DATE
                             THEN 'current'
                         WHEN CURRENT_DATE - l.due_date <= 30 THEN 'b1_30'
                         WHEN CURRENT_DATE - l.due_date <= 60 THEN 'b31_60'
                         WHEN CURRENT_DATE - l.due_date <= 90 THEN 'b61_90'
                         ELSE 'b90_plus'
                    END                               AS bucket
                FROM payment_plan_line l
                JOIN payment_plan p ON p.id = l.plan_id
                WHERE l.remaining_amount > 0
                  AND l.status != 'cancelled'
                  AND p.state NOT IN ('cancelled', 'draft')
            )
        """ % self._table)
