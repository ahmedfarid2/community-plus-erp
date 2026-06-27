{
    "name": "Advanced Warehouse & Inventory Optimization Suite",
    "version": "19.0.1.0.0",
    "category": "Inventory/Inventory",
    "summary": "Optimize inventory levels, reorder decisions, stock alerts, and "
               "slow-moving stock inside Odoo Community.",
    "description": "A generic inventory-optimization engine for Odoo Community. "
                   "Analyzes stock levels and movement history to compute stock "
                   "health, demand rate, coverage, safety stock, reorder points "
                   "and suggested reorder quantities; detects stockout/overstock/"
                   "slow-moving/dead/negative stock; and generates alerts and "
                   "reorder recommendations via a scheduled analysis. Reads stock "
                   "data read-only; purchase/procurement/approval integrations "
                   "ship as optional modules.",
    "author": "Farid",
    "license": "LGPL-3",
    "depends": ["base", "mail", "product", "stock"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/ir_sequence.xml",
        "data/ir_cron.xml",
        "views/inventory_optimization_rule_views.xml",
        "views/inventory_forecast_profile_views.xml",
        "views/inventory_supplier_lead_time_views.xml",
        "views/inventory_stock_health_views.xml",
        "views/inventory_reorder_recommendation_views.xml",
        "views/inventory_alert_views.xml",
        "views/inventory_movement_analysis_views.xml",
        "views/inventory_dead_stock_review_views.xml",
        "views/inventory_optimization_log_views.xml",
        "views/menu.xml",
    ],
    "demo": ["data/demo_data.xml"],
    "installable": True,
    "application": True,
}
