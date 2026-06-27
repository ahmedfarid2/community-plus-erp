{
    "name": "Smart Approval - Vendor Bills",
    "version": "19.0.1.0.0",
    "category": "Productivity/Approvals",
    "summary": "Require approval before posting vendor bills above a limit.",
    "description": "Connects Smart Approval Workflow to Accounting. When a "
                   "matching workflow exists (e.g. amount above a limit), "
                   "posting a vendor bill routes it through approval first. "
                   "Once approved, it posts normally.",
    "author": "Farid",
    "license": "LGPL-3",
    "depends": ["smart_approval_workflow", "account"],
    "data": [
        "views/account_move_views.xml",
    ],
    "installable": True,
    "application": False,
}
