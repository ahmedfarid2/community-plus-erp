{
    "name": "Smart Field Service - Accounting",
    "version": "19.0.1.0.0",
    "category": "Services/Field Service",
    "summary": "Create customer invoices from completed billable work orders.",
    "description": "Connects the Smart Field Service Suite to Accounting. Turns a "
                   "completed, billable work order into a customer invoice with "
                   "lines for billable parts and billable labor.",
    "author": "Farid",
    "license": "LGPL-3",
    "depends": ["smart_field_service_suite", "account"],
    "data": [
        "views/fsm_work_order_views.xml",
    ],
    "installable": True,
    "application": False,
}
