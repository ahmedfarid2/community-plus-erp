{
    "name": "Advanced Procurement & Vendor Management Suite",
    "version": "19.0.1.0.0",
    "category": "Inventory/Purchase",
    "summary": "Control purchase requests, vendor quotations, supplier "
               "comparison, approvals, contracts, and vendor performance.",
    "description": "A generic procurement and vendor-management engine for Odoo "
                   "Community: purchase requests, RFQ events, vendor quotations "
                   "with weighted scoring and comparison, split awards & savings, "
                   "vendor profiles/scorecards, performance reviews, vendor "
                   "contracts with renewal reminders, and a full audit log. "
                   "Industry-agnostic core (base + mail + product); purchase/"
                   "stock/portal/approval integrations ship as optional modules.",
    "author": "Farid",
    "license": "LGPL-3",
    "depends": ["base", "mail", "product"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/ir_sequence.xml",
        "data/ir_cron.xml",
        "views/procurement_configuration_views.xml",
        "views/procurement_vendor_profile_views.xml",
        "views/procurement_vendor_contract_views.xml",
        "views/procurement_performance_review_views.xml",
        "views/procurement_request_views.xml",
        "views/procurement_rfq_event_views.xml",
        "views/procurement_vendor_quote_views.xml",
        "views/procurement_award_views.xml",
        "views/procurement_audit_log_views.xml",
        "views/menu.xml",
    ],
    "demo": ["data/demo_data.xml"],
    "installable": True,
    "application": True,
}
