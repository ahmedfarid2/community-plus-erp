{
    "name": "Smart Approval - Purchase",
    "version": "19.0.1.0.0",
    "category": "Productivity/Approvals",
    "summary": "Require approval before confirming purchase orders.",
    "description": "Connects Smart Approval Workflow to Purchase. When a "
                   "matching workflow exists (e.g. above an amount), confirming "
                   "a purchase order routes it through the approval steps first. "
                   "Once approved, it confirms normally.",
    "author": "Farid",
    "license": "LGPL-3",
    "depends": ["smart_approval_workflow", "purchase"],
    "data": [
        "views/purchase_order_views.xml",
    ],
    "installable": True,
    "application": False,
}
