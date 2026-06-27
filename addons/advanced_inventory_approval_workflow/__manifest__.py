{
    "name": "Advanced Inventory - Approval Workflow",
    "version": "19.0.1.0.0",
    "category": "Inventory/Inventory",
    "summary": "Require approval for high-value reorders and dead-stock disposal.",
    "description": "Connects the Advanced Inventory Optimization Suite to Smart "
                   "Approval Workflow. When a matching workflow exists, approving "
                   "a high-value reorder recommendation, or completing a "
                   "dead-stock disposal, routes through the approval steps first.",
    "author": "Farid",
    "license": "LGPL-3",
    "depends": ["advanced_inventory_optimization", "smart_approval_workflow"],
    "data": [
        "views/inventory_views.xml",
    ],
    "installable": True,
    "application": False,
}
