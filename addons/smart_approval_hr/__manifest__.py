{
    "name": "Smart Approval - HR Expenses",
    "version": "19.0.1.0.0",
    "category": "Productivity/Approvals",
    "summary": "Require an extra approval for expenses above a limit.",
    "description": "Connects Smart Approval Workflow to HR Expenses. When a "
                   "matching workflow exists (e.g. amount above a limit), "
                   "approving an expense routes it through the configured "
                   "approval steps first — adding a multi-level / amount-based "
                   "gate on top of the standard expense approval.",
    "author": "Farid",
    "license": "LGPL-3",
    "depends": ["smart_approval_workflow", "hr_expense"],
    "data": [
        "views/hr_expense_views.xml",
    ],
    "installable": True,
    "application": False,
}
