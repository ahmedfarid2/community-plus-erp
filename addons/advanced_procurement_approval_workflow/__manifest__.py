{
    "name": "Advanced Procurement - Approval Workflow",
    "version": "19.0.1.0.0",
    "category": "Inventory/Purchase",
    "summary": "Require approval for high-value or high-risk procurement awards.",
    "description": "Connects the Advanced Procurement Suite to Smart Approval "
                   "Workflow. When a matching workflow exists (e.g. a domain rule "
                   "on the awarded amount or the vendor risk level), approving an "
                   "award routes it through the approval steps first. Once "
                   "approved, the award is approved.",
    "author": "Farid",
    "license": "LGPL-3",
    "depends": ["advanced_procurement_suite", "smart_approval_workflow"],
    "data": [
        "views/procurement_award_views.xml",
    ],
    "installable": True,
    "application": False,
}
