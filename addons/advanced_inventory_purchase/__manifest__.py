{
    "name": "Advanced Inventory - Purchase",
    "version": "19.0.1.0.0",
    "category": "Inventory/Purchase",
    "summary": "Convert approved reorder recommendations into purchase orders.",
    "description": "Connects the Advanced Inventory Optimization Suite to "
                   "Purchase. Turns approved reorder recommendations into "
                   "purchase orders, grouped by vendor (one PO per vendor), and "
                   "links them back.",
    "author": "Farid",
    "license": "LGPL-3",
    "depends": ["advanced_inventory_optimization", "purchase"],
    "data": [
        "views/inventory_reorder_recommendation_views.xml",
    ],
    "installable": True,
    "application": False,
}
