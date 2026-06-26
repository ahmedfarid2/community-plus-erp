{
    "name": "Subscriptions (Lite)",
    "version": "19.0.1.0.0",
    "category": "Sales/Subscriptions",
    "summary": "Clean-room recurring customer invoices for Odoo Community",
    "author": "Farid",
    "license": "LGPL-3",
    "depends": ["account", "mail", "product"],
    "data": [
        "security/ir.model.access.csv",
        "views/subscription_views.xml",
    ],
    "installable": True,
    "application": True,
}
