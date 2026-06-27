{
    "name": "Payment Plans - Accounting",
    "version": "19.0.1.0.0",
    "category": "Accounting/Payment",
    "summary": "Generate invoices from payment plan lines and sync paid amounts "
               "from customer payments.",
    "description": "Optional integration that links payment plan lines to "
                   "customer invoices: create one invoice per installment, then "
                   "keep the line's Paid Amount in sync with what the customer "
                   "has actually paid (via Odoo's standard reconciliation).",
    "author": "Farid",
    "license": "LGPL-3",
    "depends": ["payment_plan_core", "account"],
    "data": [
        "data/cron.xml",
        "views/payment_plan_account_views.xml",
    ],
    "installable": True,
    "application": False,
}
