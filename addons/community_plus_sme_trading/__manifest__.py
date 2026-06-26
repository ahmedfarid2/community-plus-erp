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
Native Community includes CRM, Sales, Purchase, Inventory, Accounting/Invoicing,
HR, Project, Manufacturing, Website/eCommerce, Point of Sale, and Expenses.
Custom clean-room modules include Financial Reports Lite, Loans Lite, Deferred
Revenue/Expense Lite, Review Reports Lite, Approvals Lite, Helpdesk Lite,
Documents Lite, and Subscriptions Lite.
Open-source addons may be installed separately after license and version audit.
""",
    "author": "Farid",
    "license": "LGPL-3",
    "depends": [
        "account",
        "account_cashflow_lite",
        "account_deferred_lite",
        "account_financial_reports_lite",
        "account_loan_lite",
        "account_review_lite",
        "appraisals_lite",
        "business_approvals_lite",
        "crm",
        "documents_lite",
        "helpdesk_lite",
        "hr",
        "hr_expense",
        "mrp",
        "point_of_sale",
        "project",
        "purchase",
        "sale_management",
        "stock",
        "subscriptions_lite",
        "website_sale",
    ],
    "data": [
        "data/community_plus_metadata.xml",
    ],
    "installable": True,
    "application": True,
}
