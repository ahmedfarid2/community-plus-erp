# Payment Plans & Collections (payment_plan_core)

> Manage scheduled payments, overdue balances, and customer follow-ups inside Odoo.

A **generic, industry-agnostic** Odoo Community app for any company that bills on a
schedule — education centers, clinics, gyms, real estate, service companies,
software agencies, B2B, maintenance, and more. It replaces the Excel sheets,
WhatsApp threads, and scattered notes used to chase scheduled and overdue payments
with a structured workflow.

This is the **dependency-light core** — it depends only on `base` and `mail`.
Accounting, sales, import and messaging features ship as separate optional modules
so the core stays clean and sellable on its own.

## What's inside

| Model | Purpose |
|-------|---------|
| `payment.plan` | The customer payment plan (totals, dates, responsible user, state). |
| `payment.plan.line` | Each scheduled installment, with computed status & overdue days. |
| `payment.plan.template` | Reusable schedules (3 monthly, 50/50, 6 monthly…). |
| `payment.plan.type` | Free-form categorization (Installments, Milestone, Retainer…). |
| `collection.followup` | Collection activities (call / WhatsApp / email / meeting…). |

The **source document** on a plan is a generic `Reference` field, not an
invoice link — so a plan can point at a sales order, invoice, project,
subscription, contract or any custom model. The selection only lists models that
are actually installed, keeping the core decoupled.

## Install

1. The module lives in `addons/payment_plan_core` (already on the addons path).
2. Update the app list and install **Payment Plans & Collections**:
   ```bash
   docker compose run --rm --no-deps web odoo -d <db> -i payment_plan_core --stop-after-init
   ```
   To include the demo records, install with demo data enabled (default on a
   fresh DB). Then restart the web service.
3. Assign users a security group: **Settings → Users** → *Payment Plans*:
   - **Payment Plan User** — sees plans/lines/follow-ups they own or are
     responsible for.
   - **Payment Plan Manager** — full access plus Templates & Plan Types config.

## Test the main flow (MVP)

1. **Configuration → Templates**: confirm the demo templates, or add one
   (e.g. *3 Monthly Payments*, monthly, equal distribution, 5 grace days).
2. **Operations → Payment Plans → New**: pick a customer, a Plan Type, set
   **Total Amount** (e.g. 3000), pick the **Template**, set a Start Date.
3. Click **Generate Lines** → three monthly lines are created and the total is
   distributed exactly (rounding lands on the last line).
4. **Activate** the plan.
5. On a line, set **Paid Amount** (e.g. 400 of 1000) → status becomes *Partial*,
   *Remaining* updates, and the plan's *Paid / Remaining / Overdue* roll up.
6. Set a line's due date in the past beyond the grace period → status becomes
   *Overdue*, *Days Overdue* fills in, and it appears under **Overdue
   Collections**.
7. **Follow-ups**: log a call on the overdue line, set a *Next Action Date*,
   then **Mark Done**.
8. Use the search filters: *Overdue*, *Due Today*, *Due This Week*, *Partial
   Payments*, *My Follow-ups*, etc.

## Extending it later (optional modules)

The core deliberately exposes clean seams:

- **`payment_plan_sale`** — add a `payment.plan` smart button on `sale.order`,
  and a "Create payment plan" action that pre-fills `source_ref` and total.
- **`payment_plan_account`** — register payments against `account.move`, sync
  `paid_amount` from reconciled invoices, post collections.
- **`payment_plan_import`** — Excel/CSV import wizard for bulk plans & lines.
- **`payment_plan_whatsapp`** — send reminders via a WhatsApp provider from a
  `collection.followup`.
- **`payment_plan_reports`** — aging buckets, collection KPIs, dashboards.

Each only `depends` on `payment_plan_core` plus its own integration target, so
the core never grows heavy dependencies. The `source_ref` selection method
(`_selection_source_ref`) is the natural extension point — override it to add
new source models.

## Design notes

- Amounts roll up from lines: `paid_amount` and `remaining_amount` on the plan
  are computed sums, always consistent with the lines.
- Line `status` is computed in strict priority: cancelled → paid → partial →
  overdue → due → pending, with the template's grace period applied before a
  line is treated as overdue.
- Constraints block negative amounts and (by default) overpayment; overpayment
  can be allowed per-call via `context={'allow_overpayment': True}`.
- Chatter (`mail.thread` + `mail.activity.mixin`) is enabled on plans and
  follow-ups for tracking and scheduled activities.

## License

LGPL-3.
