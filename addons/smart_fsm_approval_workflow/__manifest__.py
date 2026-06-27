{
    "name": "Smart Field Service - Approval Workflow",
    "version": "19.0.1.0.0",
    "category": "Services/Field Service",
    "summary": "Require approval before closing high-cost or warranty work orders.",
    "description": "Connects the Smart Field Service Suite to Smart Approval "
                   "Workflow. When a matching workflow exists (e.g. a domain rule "
                   "on the work order cost — expensive parts), the manager review "
                   "step routes through the approval steps first. Once approved, "
                   "the review proceeds.",
    "author": "Farid",
    "license": "LGPL-3",
    "depends": ["smart_field_service_suite", "smart_approval_workflow"],
    "data": [
        "views/fsm_work_order_views.xml",
    ],
    "installable": True,
    "application": False,
}
