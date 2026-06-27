"""Seed real approval requests (via the integrations) in a spread of states so
the Approvals app is clickable. Idempotent: skips if any request exists.
Run via: odoo shell -d <db> < scripts/dev/seed-approval-requests.py"""
RQ = env["approval.request"]
admin = env.ref("base.user_admin")
admin.write({
    "group_ids": [(4, env.ref("smart_approval_workflow.group_approval_admin").id)]})

if RQ.search_count([]) > 0:
    print("approval requests already exist — skipping")
else:
    reqs = []

    # 1) Payment-plan discounts above the limit -> pending requests
    plans = env["payment.plan"].search(
        [("state", "=", "active"), ("remaining_amount", ">", 1000)], limit=3)
    for plan in plans:
        plan.write({"discount_amount": 800.0,
                    "discount_reason": "Loyalty / negotiated waiver"})
        plan.action_apply_discount()
        if plan.approval_request_id:
            reqs.append(plan.approval_request_id)

    # 2) A purchase order over the limit -> pending request
    if "purchase.order" in env:
        vendor = env["res.partner"].search(
            [("is_company", "=", True)], limit=1)
        product = env["product.product"].search([], limit=1)
        if vendor and product:
            po = env["purchase.order"].create({
                "partner_id": vendor.id,
                "order_line": [(0, 0, {
                    "product_id": product.id,
                    "product_qty": 80, "price_unit": 100})]})  # 8000 > 5000
            po.button_confirm()
            if po.approval_request_id:
                reqs.append(po.approval_request_id)

    # Act on some so we have approved / pending / rejected on display.
    if len(reqs) >= 1:
        reqs[0].with_user(admin)._act("approved", "Approved — strategic account.")
    if len(reqs) >= 3:
        reqs[-1].with_user(admin)._act(
            "rejected", "Budget not available this quarter.")

    env.cr.commit()
    print("created %s requests" % len(reqs))

print("Requests now: total=%s | %s" % (
    RQ.search_count([]),
    {s: RQ.search_count([("state", "=", s)])
     for s in ("pending", "approved", "rejected")}))
