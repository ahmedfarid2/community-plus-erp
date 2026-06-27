{
    "name": "Smart CPQ - Sales",
    "version": "19.0.1.0.0",
    "category": "Sales/CPQ",
    "summary": "Create a sale quotation from a validated CPQ configuration.",
    "description": "Connects Smart CPQ to Sales. Turns a validated configuration "
                   "into a sale.order with one line carrying the configured price "
                   "and a readable summary of the selected options.",
    "author": "Farid",
    "license": "LGPL-3",
    "depends": ["smart_cpq_builder", "sale"],
    "data": [
        "views/cpq_configuration_views.xml",
    ],
    "installable": True,
    "application": False,
}
