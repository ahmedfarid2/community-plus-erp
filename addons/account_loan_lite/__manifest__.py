{
    "name": "Loans (Lite)",
    "version": "19.0.1.0.0",
    "category": "Accounting/Accounting",
    "summary": "Loan management with amortization schedule for Odoo Community",
    "author": "Farid",
    "license": "LGPL-3",
    "depends": ["community_plus_theme", "account"],
    "data": [
        "security/ir.model.access.csv",
        "report/loan_report.xml",
        "views/loan_views.xml",
    ],
    "installable": True,
    "application": False,
}
