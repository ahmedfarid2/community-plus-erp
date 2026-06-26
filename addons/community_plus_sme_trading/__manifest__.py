{
    "name": "Community Plus - SME Trading Pack",
    "version": "19.0.1.0.0",
    "category": "Productivity",
    "summary": "Legal Community Plus ERP pack for trading companies",
    "description": """
Installs the standard Community apps used by the Community Plus SME Trading
offer. This module is a clean-room pack: it does not contain or depend on
unlicensed Odoo Enterprise code.

Feature source labels:
- Native Community: CRM, Sales, Purchase, Inventory, Accounting/Invoicing, HR,
  Project, Manufacturing, Website/eCommerce, Point of Sale, Expenses.
- Custom clean-room modules: Loans Lite, Deferred Revenue/Expense Lite.
- Open-source addon: optional third-party addons audited and installed outside
  this pack when available for the target Odoo version.
""",
    "author": "Farid",
    "license": "LGPL-3",
    "depends": [
        "account",
        "account_deferred_lite",
        "account_loan_lite",
        "crm",
        "hr",
        "hr_expense",
        "mrp",
        "point_of_sale",
        "project",
        "purchase",
        "sale_management",
        "stock",
        "website_sale",
    ],
    "data": [
        "data/community_plus_metadata.xml",
    ],
    "installable": True,
    "application": True,
}
