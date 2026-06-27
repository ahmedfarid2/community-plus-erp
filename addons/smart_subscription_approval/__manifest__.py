{
    "name": "Smart Subscription - Approval Workflow",
    "version": "19.0.1.0.0",
    "category": "Sales/Subscriptions",
    "summary": "Require approval before cancelling high-value subscriptions.",
    "description": "Connects Smart Subscription Manager to Smart Approval "
                   "Workflow. When a matching workflow exists (e.g. a domain rule "
                   "on MRR), cancelling a subscription routes it through the "
                   "approval steps first — churn control for valuable accounts. "
                   "Once approved, the cancellation proceeds.",
    "author": "Farid",
    "license": "LGPL-3",
    "depends": ["smart_subscription_manager", "smart_approval_workflow"],
    "data": [
        "views/subscription_views.xml",
    ],
    "installable": True,
    "application": False,
}
