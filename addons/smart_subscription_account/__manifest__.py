{
    "name": "Smart Subscription - Accounting",
    "version": "19.0.1.0.0",
    "category": "Sales/Subscriptions",
    "summary": "Generate customer invoices from subscription billing lines and "
               "sync payment status.",
    "description": "Connects Smart Subscription Manager to Accounting. Create a "
                   "customer invoice from a due billing line (or all due lines on "
                   "a subscription), then keep the line's paid amount in sync with "
                   "what the customer has paid via standard reconciliation.",
    "author": "Farid",
    "license": "LGPL-3",
    "depends": ["smart_subscription_manager", "account"],
    "data": [
        "data/ir_cron.xml",
        "views/subscription_views.xml",
    ],
    "installable": True,
    "application": False,
}
