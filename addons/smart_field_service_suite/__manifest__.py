{
    "name": "Smart Field Service & Maintenance Suite",
    "version": "19.0.1.0.0",
    "category": "Services/Field Service",
    "summary": "Manage field service work orders, technicians, SLAs, spare parts, "
               "recurring maintenance, and customer assets inside Odoo Community.",
    "description": "A generic field-service and maintenance operations engine for "
                   "Odoo Community: service requests, work orders, technician "
                   "dispatch & scheduling, SLA tracking, checklists, time & parts, "
                   "customer assets and service history, recurring maintenance "
                   "contracts, and customer sign-off. Industry-agnostic core "
                   "(base + mail + product); sale/account/inventory/portal/mobile "
                   "integrations ship as optional modules.",
    "author": "Farid",
    "license": "LGPL-3",
    "depends": ["base", "mail", "product"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/ir_sequence.xml",
        "data/ir_cron.xml",
        "views/fsm_configuration_views.xml",
        "views/fsm_service_location_views.xml",
        "views/fsm_customer_asset_views.xml",
        "views/fsm_technician_views.xml",
        "views/fsm_team_views.xml",
        "views/fsm_service_request_views.xml",
        "views/fsm_work_order_views.xml",
        "views/fsm_maintenance_contract_views.xml",
        "views/fsm_operation_log_views.xml",
        "views/menu.xml",
    ],
    "demo": [
        "data/demo_data.xml",
    ],
    "installable": True,
    "application": True,
}
