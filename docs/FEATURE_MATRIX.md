# Community Plus — feature matrix

This product is **Odoo Community Plus ERP**: Odoo Community + audited open-source
addons + custom clean-room modules. **Do not** market it as official Odoo Enterprise
unless the client buys a valid Enterprise subscription.

Legend — **source** of each capability:
- 🟢 **Native Community** — official Odoo Community image
- 🔵 **Open-source addon** — vetted LGPL (Odoo Mates), pinned revision
- 🟣 **Custom clean-room** — written for this project, no Enterprise code copied
- 💲 **Enterprise-only** — needs a paid subscription / external service (NOT shipped)

---

## Accounting & Finance

| Capability | Source | Module |
|---|---|---|
| Chart of accounts, journals, entries, taxes, payments, bank reconcile | 🟢 | `account` |
| Full Accounting app UI + PDF reports (Balance Sheet, P&L, GL, Partner Ledger, Aged, Tax) | 🔵 | `om_account_accountant` / `accounting_pdf_reports` |
| Assets + depreciation posting | 🔵 / 🟣 | `om_account_asset`, `account_*_lite` |
| Budgets, Fiscal Year, Follow-ups, Recurring entries | 🔵 | Odoo Mates suite |
| **Cash Flow statement** | 🟣 | `account_cashflow_lite` |
| **Loans + amortization** | 🟣 | `account_loan_lite` |
| **Deferred Revenue/Expense** | 🟣 | `account_deferred_lite` |
| **Review** (to-invoice / to-bill / not-delivered / not-received) | 🟣 | `account_review_lite` |
| Trial Balance / P&L / BS / GL / Aged / Tax (alt. custom) | 🟣 | `account_financial_reports_lite` |
| Bank sync (live feeds), AI invoice OCR | 💲 | — paid services, not shipped |

## Human Resources

| Capability | Source | Module |
|---|---|---|
| Employees, Recruitment, Time Off, Expenses, Attendances, Skills, Fleet | 🟢 | `hr*`, `fleet` |
| **Payroll** + payroll accounting | 🔵 | `om_hr_payroll(_account)` |
| Timesheets, Presence, Work Entries, Recruitment Survey, Hourly Cost | 🟢 | `hr_timesheet`, `hr_presence`, … |
| **Appraisals** | 🟣 | `appraisals_lite` |
| **Planning** (shift scheduling) | 🟣 | `planning_lite` |
| **Referrals** | 🟣 | `referrals_lite` |

## Sales / CRM

| Capability | Source | Module |
|---|---|---|
| CRM, Sales, eCommerce, POS | 🟢 | `crm`, `sale_management`, `website_sale`, `point_of_sale` |
| **Loyalty / Coupons / Promotions / Gift Cards** | 🟢 | `sale_loyalty`, `pos_loyalty` |
| Margins, POS discounts, Product Matrix, Event Booths | 🟢 | `sale_margin`, `pos_discount`, … |
| **Subscriptions** (recurring billing, MRR/churn, upsells, templates) | 🟣 | `subscriptions_lite` |
| **Helpdesk** | 🟣 | `helpdesk_lite` |
| **Sign** (signature requests) | 🟣 | `sign_lite` |
| Amazon connector, Social marketing | 💲 | — external APIs, not shipped |

## Services

| Capability | Source | Module |
|---|---|---|
| Project, To-Do, Timesheets | 🟢 | `project`, `hr_timesheet` |
| **Field Service** (on-site orders) | 🟣 | `field_service_lite` |
| **Appointments** (booking + calendar) | 🟣 | `appointment_lite` |
| Helpdesk, Planning | 🟣 | `helpdesk_lite`, `planning_lite` |
| Timesheet *grid* widget | 💲 | Enterprise UI widget (data available in list/form) |

## Supply Chain & Manufacturing

| Capability | Source | Module |
|---|---|---|
| Inventory, Purchase, Manufacturing, Repairs, Maintenance | 🟢 | `stock`, `purchase`, `mrp`, … |
| **Subcontracting** | 🟢 | `mrp_subcontracting` |
| **Purchase Requisitions / Tenders** | 🟢 | `purchase_requisition` |
| **Dropshipping** | 🟢 | `stock_dropshipping` |
| **Quality** (control points + checks) | 🟣 | `quality_lite` |
| Barcode (scanner), PLM, Shop Floor/Work Orders | 💲 | hardware widget / deep MES, not shipped |

## Website / Marketing

| Capability | Source | Module |
|---|---|---|
| Website, eCommerce, Blog, Forum | 🟢 | `website*`, `website_blog`, `website_forum` |
| Email Marketing, SMS Marketing, Events, Surveys | 🟢 | `mass_mailing*`, `event`, `survey` |
| **Marketing Automation** (campaigns + steps + participants) | 🟣 | `marketing_automation_lite` |
| Social Marketing | 💲 | social-media APIs, not shipped |

## Productivity

| Capability | Source | Module |
|---|---|---|
| Discuss, Calendar, Contacts, Knowledge-style notes | 🟢 | `mail`, `calendar`, `contacts` |
| **Approvals** | 🟣 | `business_approvals_lite` |
| **Documents** (filing + expiry reminders) | 🟣 | `documents_lite` |

---

## OCA power add-ons (vetted open-source, in `addons/oca/`)

The official **Odoo Community Association** modules — code-reviewed, production-grade.
Several **close gaps previously marked Enterprise-only**:

| Module | Adds | Closes |
|---|---|---|
| `account_reconcile_oca` | Bank **reconciliation widget** | ✅ Enterprise reconcile widget |
| `account_statement_import_qif/camt` | **Import bank statements** (QIF/CAMT files) | ✅ partial free alt. to bank sync |
| `auditlog` | **Audit trail** (who changed what, when) | ✅ Enterprise Audit Trail |
| `report_xlsx` | **Excel export** on any report | ✅ Excel exports |
| `mis_builder` | Formula-based financial statements / KPI dashboards | Powerful reporting |
| `web_responsive` | Modern responsive backend UI | Enterprise-like UX |
| `queue_job` | Async background jobs | Production scalability |
| `account_move_name_sequence`, `account_journal_lock_date` | Sequence + period-lock controls | Accounting hardening |
| `partner_firstname` | First/last name on contacts | Quality of life |

Fetched by `scripts/dev/fetch-thirdparty.sh`; available in `addons_path` for any client.

## What is *still* genuinely Enterprise-only (never shipped, never faked)

These need a **paid subscription or external service** — no free code reproduces them:
**live bank-feed auto-sync, AI invoice OCR, barcode scanning hardware widget, Social
Marketing (social APIs), Amazon connector, full PLM / Shop-Floor MES, the Timesheet grid
widget.** (Note: bank *statement file import* and *reconciliation* are now covered free by
OCA above — only the *live auto-sync feed* remains paid.)

## Custom clean-room modules (17, all LGPL-3, our code)

`account_cashflow_lite`, `account_deferred_lite`, `account_financial_reports_lite`,
`account_loan_lite`, `account_review_lite`, `appraisals_lite`, `appointment_lite`,
`business_approvals_lite`, `documents_lite`, `field_service_lite`, `helpdesk_lite`,
`marketing_automation_lite`, `planning_lite`, `quality_lite`, `referrals_lite`,
`sign_lite`, `subscriptions_lite`. Bundled by `community_plus_sme_trading`.

## License rule

Every shipped module must be one of:
- 🟢 **Native Community** from the official Odoo Community image.
- 🔵 **Open-source addon** with an audited license and pinned source revision.
- 🟣 **Custom clean-room module** written for this project without copying Enterprise
  source code, assets, views, or proprietary behavior text.

Verify before any delivery: `make pack-test` (must PASS) — see
[DELIVERY_CHECKLIST.md](DELIVERY_CHECKLIST.md).
