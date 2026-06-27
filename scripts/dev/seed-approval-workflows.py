"""Seed ready-made approval workflows + grant admin the Approval roles.
Idempotent (keyed on workflow name). Run via:
  odoo shell -d <db> < scripts/dev/seed-approval-workflows.py
Only creates a workflow when its target model/field exists (the matching
integration module is installed)."""
WF = env["approval.workflow"]
ST = env["approval.workflow.step"]
F = env["ir.model.fields"]
Model = env["ir.model"]
mgr = env.ref("smart_approval_workflow.group_approval_manager")

env.ref("base.user_admin").write({
    "group_ids": [(4, env.ref("smart_approval_workflow.group_approval_admin").id)]})


def field_id(model, name):
    f = F.search([("model", "=", model), ("name", "=", name)], limit=1)
    return f.id if f else False


def ensure_workflow(spec):
    name, model = spec["name"], spec["model"]
    if model not in env:
        return "skip (model %s not installed)" % model
    if WF.search([("name", "=", name)], limit=1):
        return "exists"
    vals = {
        "name": name,
        "model_id": Model.search([("model", "=", model)], limit=1).id,
        "condition_type": spec["condition"],
    }
    if spec["condition"] == "amount_based":
        fid = field_id(model, spec["field"])
        if not fid:
            return "skip (field %s.%s not found)" % (model, spec["field"])
        vals.update(amount_field_id=fid, minimum_amount=spec["minimum"])
    elif spec["condition"] == "domain_based":
        vals["domain_filter"] = spec["domain"]
    wf = WF.create(vals)
    ST.create({
        "workflow_id": wf.id, "sequence": 10, "name": spec["step"],
        "approver_type": "group", "approver_group_id": mgr.id,
        "required_approval_count": 1,
    })
    return "created"


plan = [
    {"name": "Purchase Order over 5,000", "model": "purchase.order",
     "condition": "amount_based", "field": "amount_total", "minimum": 5000.0,
     "step": "Purchasing Manager"},
    {"name": "Vendor Bill over 5,000", "model": "account.move",
     "condition": "amount_based", "field": "amount_total", "minimum": 5000.0,
     "step": "Finance Manager"},
    {"name": "Sales Discount over 1,000", "model": "sale.order",
     "condition": "amount_based", "field": "discount_total", "minimum": 1000.0,
     "step": "Sales Manager"},
    {"name": "Payment Plan Discount over 500", "model": "payment.plan",
     "condition": "amount_based", "field": "discount_amount", "minimum": 500.0,
     "step": "Finance Manager"},
    {"name": "Expense over 300", "model": "hr.expense",
     "condition": "amount_based", "field": "total_amount", "minimum": 300.0,
     "step": "Finance Manager"},
    {"name": "Approve Outgoing Deliveries", "model": "stock.picking",
     "condition": "domain_based",
     "domain": "[('picking_type_code', '=', 'outgoing')]",
     "step": "Warehouse Manager"},
    {"name": "CPQ Low Margin (< 15%)", "model": "cpq.configuration",
     "condition": "domain_based",
     "domain": "[('margin_percent', '<', 15)]",
     "step": "Sales Director"},
    {"name": "High-value Subscription Cancellation (MRR >= 500)",
     "model": "subscription.subscription", "condition": "domain_based",
     "domain": "[('mrr_amount', '>=', 500)]",
     "step": "Retention Manager"},
]

for spec in plan:
    print("  %-32s -> %s" % (spec["name"], ensure_workflow(spec)))

env.cr.commit()
print("Workflows now configured:", WF.search_count([]))
