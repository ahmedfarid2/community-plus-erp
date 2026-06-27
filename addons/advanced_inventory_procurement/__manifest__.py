{
    "name": "Advanced Inventory - Procurement",
    "version": "19.0.1.0.0",
    "category": "Inventory/Purchase",
    "summary": "Turn approved reorder recommendations into procurement requests "
               "for supplier comparison.",
    "description": "Bridges the Advanced Inventory Optimization Suite and the "
                   "Advanced Procurement Suite. Instead of creating a purchase "
                   "order directly, approved reorder recommendations become a "
                   "purchase request with a line per recommendation — which the "
                   "procurement team can take through RFQ, vendor comparison and "
                   "award.",
    "author": "Farid",
    "license": "LGPL-3",
    "depends": ["advanced_inventory_optimization", "advanced_procurement_suite"],
    "data": [
        "views/inventory_reorder_recommendation_views.xml",
    ],
    "installable": True,
    "application": False,
}
