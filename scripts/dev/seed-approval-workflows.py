"""Seed ready-made approval workflows + grant admin the Approval roles.
Idempotent (keyed on workflow name). Run via:
  odoo shell -d <db> < scripts/dev/seed-approval-workflows.py
Only creates a workflow when its target model/field is available (the matching
integration module is installed)."""
WF = env["approval.workflow"]
ST = env["approval.workflow.step"]
F = env["ir.model.fields"]
Model = env["ir.model"]
mgr = env.ref("smart_approval_workflow.group_approval_manager")

# Admin can configure + approve everything
env.ref("base.user_admin").write({
    "group_ids": [(4, env.ref("smart_approval_workflow.group_approval_admin").id)]})


def field_id(model, name):
    f = F.search([("model", "=", model), ("name", "=", name)], limit=1)
    return f.id if f else False


def ensure_workflow(name, model, amount_field, minimum, step_name):
    if model not in env:
        return "skip (model %s not installed)" % model
    fid = field_id(model, amount_field)
    if not fid:
        return "skip (field %s.%s not found)" % (model, amount_field)
    if WF.search([("name", "=", name)], limit=1):
        return "exists"
    model_rec = Model.search([("model", "=", model)], limit=1)
    wf = WF.create({
        "name": name, "model_id": model_rec.id,
        "condition_type": "amount_based",
        "amount_field_id": fid, "minimum_amount": minimum,
    })
    ST.create({
        "workflow_id": wf.id, "sequence": 10, "name": step_name,
        "approver_type": "group", "approver_group_id": mgr.id,
        "required_approval_count": 1,
    })
    return "created"


plan = [
    ("Purchase Order over 5,000", "purchase.order", "amount_total", 5000.0,
     "Purchasing Manager"),
    ("Vendor Bill over 5,000", "account.move", "amount_total", 5000.0,
     "Finance Manager"),
    ("Sales Discount over 1,000", "sale.order", "discount_total", 1000.0,
     "Sales Manager"),
    ("Payment Plan Discount over 500", "payment.plan", "discount_amount", 500.0,
     "Finance Manager"),
]

for name, model, fld, minimum, step in plan:
    print("  %-34s -> %s" % (name, ensure_workflow(name, model, fld, minimum, step)))

env.cr.commit()
print("Workflows now configured:", WF.search_count([]))
