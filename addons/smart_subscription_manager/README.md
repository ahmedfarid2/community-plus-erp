# Smart Subscription & Recurring Revenue Manager (smart_subscription_manager)

> Manage subscriptions, recurring billing, renewals, and customer lifecycle inside Odoo Community.

A generic recurring-revenue engine for Odoo 19 Community — for SaaS, training,
maintenance, gyms, clinics, agencies, hosting, rentals and membership businesses.
Industry-agnostic core (`base` + `mail` + `product`); accounting/sales/payment/
portal integrations ship as optional modules.

## Models

| Model | Purpose |
|-------|---------|
| `subscription.plan` | Reusable package: billing cycle, price, trial, term, auto-renew. |
| `subscription.subscription` | A customer subscription with full state machine. |
| `subscription.billing.line` | One scheduled recurring billing period. |
| `subscription.lifecycle.event` | Full history of every lifecycle action. |
| `subscription.pause` | Pause periods. |
| `subscription.change` | Upgrades / downgrades / plan & price changes. |
| `subscription.cancellation.reason` | Churn reasons. |
| `subscription.metric.snapshot` | MRR/ARR/churn metrics over time. |

## Install
```bash
docker compose run --rm --no-deps web odoo -d <db> -i smart_subscription_manager --stop-after-init
docker compose restart web
```
Assign users under **Settings → Users → Subscriptions**: User / Manager / Administrator.

## Test the main flow
1. **Subscriptions → Plans** (Administrator): review the demo plans (SaaS, Gym,
   Maintenance, Service) or create one (billing period, interval, price, trial).
2. **Subscriptions → New**: pick a customer and plan — price/trial/auto-renew copy
   from the plan. **Start Trial** or **Activate**.
3. **Generate Billing Schedule** → billing lines are created per cycle; the
   summary footer shows MRR/ARR.
4. On a billing line: **Mark as Paid / Partially Paid / Skip**. Back-date a due
   date and run the maintenance cron → it flips to **Overdue**.
5. **Pause** → **Resume**; **Upgrade/Downgrade** (wizard) logs a plan change;
   **Renew** extends the renewal/end date; **Cancel** (wizard) records a churn
   reason. Every action appears under **Lifecycle**.

## Billing schedule generation
`Generate Billing Schedule` (or `_generate_billing_lines`) starts from
`next_billing_date` (or trial end / start), steps by the plan's period × interval,
and creates one line per cycle until `end_date` (if set), the minimum-contract
horizon, or a 12-cycle default. A unique constraint on
`(subscription, period_start)` prevents duplicate periods, so it is safe to re-run.

## Trial / renew / pause / resume / upgrade / downgrade
- **Trial** sets `trial_end_date`; the cron (or **Activate**) moves it to *active*.
- **Renew** (manual or auto) extends `renewal_date`/`end_date` by the term and logs
  a `renewed` event.
- **Pause** creates a `subscription.pause` and stops billing generation; **Resume**
  closes the pause and reactivates.
- **Upgrade/Downgrade** (wizard) records a `subscription.change` (old/new plan &
  price, effective date, proration policy) and updates the subscription.

## MRR / ARR
Each cycle length is normalized to months (`daily≈1/30, weekly≈7/30, monthly=1,
quarterly=3, semi_annual=6, annual=12`, × interval). `MRR = current_amount /
months`, `ARR = MRR × 12`, where `current_amount` is the price after % and fixed
discounts. MRR counts only trial/active/paused subscriptions.

## Scheduled actions
- **Daily maintenance** (`_cron_subscription_maintenance`): ends trials, expires
  fixed-term non-auto-renew subscriptions, auto-renews due ones, flips overdue
  billing lines, and schedules renewal-reminder activities (14 days out).
- **Monthly metric snapshot** (`_cron_snapshot_metrics`): records counts, MRR/ARR,
  net MRR vs the previous snapshot, and churn rate.

## Extending later
Optional modules `depend = ['smart_subscription_manager', <target>]`:
`smart_subscription_sale` (create from sale orders), `_account` (invoices + payment
sync), `_payment`, `_portal`, `_website`, `_reports` (MRR/ARR/churn dashboards),
`_ai_churn`, `_approval` (approve discounts/cancellations/plan changes via Smart
Approval), `_payment_plan` (installments for annual prepay), `_whatsapp` (reminders).

## License
LGPL-3.
