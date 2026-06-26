{
    "name": "Field Service (Lite)",
    "version": "19.0.1.0.0",
    "category": "Services/Field Service",
    "summary": "Clean-room on-site field service orders for Odoo Community",
    "author": "Farid",
    "license": "LGPL-3",
    "depends": ["hr", "mail"],
    "data": [
        "security/ir.model.access.csv",
        "views/fsm_views.xml",
    ],
    "installable": True,
    "application": True,
}
