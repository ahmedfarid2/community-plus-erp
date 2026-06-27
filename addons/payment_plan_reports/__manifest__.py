{
    "name": "Payment Plans - Reports",
    "version": "19.0.1.0.0",
    "category": "Accounting/Payment",
    "summary": "Aging report for payment plan lines (current / 1-30 / 31-60 / "
               "61-90 / 90+).",
    "description": "Adds an Aging analysis (pivot, graph, list) over outstanding "
                   "payment plan lines, bucketed by how long they are overdue. "
                   "Read-only SQL view — no extra storage.",
    "author": "Farid",
    "license": "LGPL-3",
    "depends": ["payment_plan_core"],
    "data": [
        "security/ir.model.access.csv",
        "views/payment_plan_aging_views.xml",
    ],
    "installable": True,
    "application": False,
}
