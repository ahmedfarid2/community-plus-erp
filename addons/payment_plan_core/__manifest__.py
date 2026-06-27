{
    "name": "Payment Plans & Collections",
    "version": "19.0.1.0.0",
    "category": "Accounting/Payment",
    "summary": "Manage scheduled payments, overdue balances, and customer "
               "follow-ups inside Odoo.",
    "description": "Generic, industry-agnostic management of scheduled customer "
                   "payments, installment plans, overdue balances, partial "
                   "payments and collection follow-ups. Dependency-light core "
                   "(base + mail); accounting/sales/messaging integrations ship "
                   "as separate optional modules.",
    "author": "Farid",
    "website": "",
    "license": "LGPL-3",
    "depends": ["base", "mail"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/ir_sequence.xml",
        "views/payment_plan_views.xml",
        "views/payment_plan_line_views.xml",
        "views/payment_plan_template_views.xml",
        "views/payment_plan_type_views.xml",
        "views/collection_followup_views.xml",
        "views/menu.xml",
    ],
    "demo": [
        "data/demo_data.xml",
    ],
    "installable": True,
    "application": True,
}
