{
    "name": "Financial Reports (Lite)",
    "version": "19.0.1.0.0",
    "category": "Accounting/Accounting",
    "summary": "Trial Balance, Profit & Loss and Balance Sheet for Odoo Community",
    "description": """
Free financial reports on top of the Community 'account' module:
- Trial Balance (per-account debit / credit / balance for a period)
- Profit & Loss summary (income vs. expense -> net profit)
- Balance Sheet summary (assets / liabilities / equity)
Interactive view + printable PDF. No Enterprise license required.
""",
    "author": "Farid",
    "license": "LGPL-3",
    "depends": ["account"],
    "data": [
        "security/ir.model.access.csv",
        "report/financial_report.xml",
        "views/trial_balance_views.xml",
        "views/more_reports_views.xml",
        "views/tax_report_views.xml",
        "views/accounting_app_views.xml",
        "views/dashboard_views.xml",
    ],
    # Clean-room Community Plus accounting reports. No Enterprise code dependency.
    "installable": True,
    "application": False,
}
