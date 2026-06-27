{
    "name": "Advanced Procurement - Purchase",
    "version": "19.0.1.0.0",
    "category": "Inventory/Purchase",
    "summary": "Convert approved procurement awards into purchase orders.",
    "description": "Connects the Advanced Procurement Suite to Purchase. Turns an "
                   "approved award into a purchase.order (one per awarded vendor) "
                   "carrying the awarded lines, and links it back for full RFQ "
                   "traceability.",
    "author": "Farid",
    "license": "LGPL-3",
    "depends": ["advanced_procurement_suite", "purchase"],
    "data": [
        "views/procurement_award_views.xml",
    ],
    "installable": True,
    "application": False,
}
