{
    "name": "Smart Subscription & Recurring Revenue Manager",
    "version": "19.0.1.0.0",
    "category": "Sales/Subscriptions",
    "summary": "Manage subscriptions, recurring billing, renewals, and customer "
               "lifecycle inside Odoo Community.",
    "description": "A generic recurring-revenue engine for Odoo Community. Define "
                   "subscription plans and billing cycles, run the full lifecycle "
                   "(trial, activate, pause/resume, upgrade/downgrade, renew, "
                   "cancel, expire), generate recurring billing schedules, track "
                   "MRR/ARR/churn and customer health, and automate renewals and "
                   "overdue handling with scheduled actions. Industry-agnostic "
                   "core (base + mail + product); account/sale/payment/portal "
                   "integrations ship as optional modules.",
    "author": "Farid",
    "license": "LGPL-3",
    "depends": ["base", "mail", "product"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/ir_sequence.xml",
        "data/ir_cron.xml",
        "wizard/subscription_cancel_wizard_views.xml",
        "wizard/subscription_change_wizard_views.xml",
        "views/subscription_plan_views.xml",
        "views/subscription_subscription_views.xml",
        "views/subscription_billing_line_views.xml",
        "views/subscription_lifecycle_event_views.xml",
        "views/subscription_pause_views.xml",
        "views/subscription_change_views.xml",
        "views/subscription_cancellation_reason_views.xml",
        "views/subscription_metric_snapshot_views.xml",
        "views/menu.xml",
    ],
    "demo": [
        "data/demo_data.xml",
    ],
    "installable": True,
    "application": True,
}
