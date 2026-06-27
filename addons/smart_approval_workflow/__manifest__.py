{
    "name": "Smart Approval Workflow",
    "version": "19.0.1.0.0",
    "category": "Productivity/Approvals",
    "summary": "Create configurable approval workflows for any Odoo document.",
    "description": "A generic, reusable approval engine for Odoo Community. "
                   "Define multi-level approval workflows for any model "
                   "(purchase orders, bills, expenses, discounts, HR requests, "
                   "contracts…), with amount- and domain-based rules, full "
                   "approval history, approver activities and audit trail. "
                   "Dependency-light core (base + mail); purchase/account/sale/"
                   "inventory/HR integrations ship as optional modules.",
    "author": "Farid",
    "license": "LGPL-3",
    "depends": ["base", "mail"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/ir_sequence.xml",
        "wizard/approval_action_wizard_views.xml",
        "views/approval_workflow_views.xml",
        "views/approval_request_views.xml",
        "views/menu.xml",
    ],
    "demo": [
        "data/demo_data.xml",
    ],
    "installable": True,
    "application": True,
}
