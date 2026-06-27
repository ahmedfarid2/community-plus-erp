{
    "name": "Smart Approval - Payment Plans",
    "version": "19.0.1.0.0",
    "category": "Productivity/Approvals",
    "summary": "Require approval for payment-plan discounts and waivers above a "
               "limit.",
    "description": "Connects Smart Approval Workflow to Payment Plans. Propose a "
                   "discount or waiver on a plan; if it meets a configured "
                   "amount-based workflow (e.g. above a limit) it must be "
                   "approved before it is applied to the plan's lines.",
    "author": "Farid",
    "license": "LGPL-3",
    "depends": ["smart_approval_workflow", "payment_plan_core"],
    "data": [
        "views/payment_plan_views.xml",
    ],
    "installable": True,
    "application": False,
}
