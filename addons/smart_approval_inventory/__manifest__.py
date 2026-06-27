{
    "name": "Smart Approval - Inventory",
    "version": "19.0.1.0.0",
    "category": "Productivity/Approvals",
    "summary": "Require approval before validating stock transfers.",
    "description": "Connects Smart Approval Workflow to Inventory. When a "
                   "matching workflow exists (typically always- or domain-based, "
                   "e.g. a specific operation type or location), validating a "
                   "transfer routes it through approval first.",
    "author": "Farid",
    "license": "LGPL-3",
    "depends": ["smart_approval_workflow", "stock"],
    "data": [
        "views/stock_picking_views.xml",
    ],
    "installable": True,
    "application": False,
}
