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
        "data/cron.xml",
        "views/subscription_views.xml",
        "views/mrr_log_views.xml",
        "views/config_views.xml",
        "views/extra_menus.xml",
    ],
    "installable": True,
    "application": True,
}
