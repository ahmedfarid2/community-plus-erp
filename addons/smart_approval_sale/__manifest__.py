{
    "name": "Smart Approval - Sales",
    "version": "19.0.1.0.0",
    "category": "Productivity/Approvals",
    "summary": "Require approval before confirming sales orders with big discounts.",
    "description": "Connects Smart Approval Workflow to Sales. Adds the total "
                   "discount given on a sales order and, when a matching workflow "
                   "exists (e.g. discount above a limit), routes the order "
                   "through approval before it can be confirmed.",
    "author": "Farid",
    "license": "LGPL-3",
    "depends": ["smart_approval_workflow", "sale"],
    "data": [
        "views/sale_order_views.xml",
    ],
    "installable": True,
    "application": False,
}
