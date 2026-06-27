{
    "name": "Smart CPQ & Quotation Builder",
    "version": "19.0.1.0.0",
    "category": "Sales/CPQ",
    "summary": "Configure complex products, calculate prices automatically, and "
               "generate accurate quotations inside Odoo.",
    "description": "A generic Configure-Price-Quote engine for Odoo Community. "
                   "Build configurable products or service packages from option "
                   "groups, options, pricing rules and compatibility rules; "
                   "validate selections; calculate dynamic prices with a SAFE "
                   "formula evaluator (no raw eval); and track margins and a full "
                   "calculation log. Industry-agnostic core (base + mail + "
                   "product); sale/MRP/website/reports integrations ship as "
                   "optional modules.",
    "author": "Farid",
    "license": "LGPL-3",
    "depends": ["base", "mail", "product"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/ir_sequence.xml",
        "views/cpq_template_views.xml",
        "views/cpq_option_group_views.xml",
        "views/cpq_option_views.xml",
        "views/cpq_pricing_rule_views.xml",
        "views/cpq_compatibility_rule_views.xml",
        "views/cpq_configuration_views.xml",
        "views/cpq_calculation_log_views.xml",
        "views/menu.xml",
    ],
    "demo": [
        "data/demo_data.xml",
    ],
    "installable": True,
    "application": True,
}
