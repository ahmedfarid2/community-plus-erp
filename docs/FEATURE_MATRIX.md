# Community Plus feature matrix

This product is sold as **Odoo Community Plus ERP**: Odoo Community, audited
open-source addons, and custom clean-room modules. Do not market it as official
Odoo Enterprise unless the client buys a valid Enterprise subscription.

| Area | Source | First-pack coverage |
|---|---|---|
| CRM | Native Community | Leads, pipeline, activities, opportunities |
| Sales | Native Community | Quotations, sales orders, invoicing handoff |
| Purchase | Native Community | RFQs, purchase orders, vendor bills |
| Inventory | Native Community | Warehouses, receipts, deliveries, stock moves |
| Accounting/Invoicing | Native Community + addon/custom where needed | Journals, invoices, payments, taxes, core reports |
| Loans | Custom clean-room module | Amortization schedules through `account_loan_lite` |
| Expenses | Native Community | Employee expenses and accounting handoff |
| HR basics | Native Community | Employees and departments |
| Project | Native Community | Projects, tasks, collaboration |
| Manufacturing | Native Community | BoMs, manufacturing orders |
| Website/eCommerce | Native Community | Website, shop, online orders |
| Point of Sale | Native Community | POS sessions and accounting handoff |
| Approvals | Custom clean-room module | Implemented lite workflow |
| Documents-lite | Custom clean-room module | Implemented lite filing |
| Helpdesk-lite | Custom clean-room module | Implemented lite ticketing |
| Subscriptions-lite | Custom clean-room module | Implemented recurring invoices |
| Advanced financial reports | Open-source addon or custom clean-room module | Planned after Odoo 19 compatibility audit |

## License rule

Every shipped module must be one of:

- **Native Community** from the official Odoo Community image.
- **Open-source addon** with an audited license and pinned source revision.
- **Custom clean-room module** written for this project without copying Enterprise
  source code, assets, views, or proprietary behavior text.
