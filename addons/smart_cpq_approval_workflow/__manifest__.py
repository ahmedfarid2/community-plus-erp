{
    "name": "Smart CPQ - Approval Workflow",
    "version": "19.0.1.0.0",
    "category": "Sales/CPQ",
    "summary": "Require approval before validating low-margin / high-discount "
               "CPQ configurations.",
    "description": "Connects Smart CPQ to Smart Approval Workflow. When a "
                   "matching workflow exists (e.g. a domain rule on a low margin "
                   "percentage), validating a configuration routes it through the "
                   "approval steps first. Once approved, it validates normally.",
    "author": "Farid",
    "license": "LGPL-3",
    "depends": ["smart_cpq_builder", "smart_approval_workflow"],
    "data": [
        "views/cpq_configuration_views.xml",
    ],
    "installable": True,
    "application": False,
}
