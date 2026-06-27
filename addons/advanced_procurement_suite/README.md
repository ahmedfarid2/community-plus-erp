# Advanced Procurement & Vendor Management Suite (advanced_procurement_suite)

> Control purchase requests, vendor quotations, supplier comparison, approvals, contracts, and vendor performance inside Odoo Community.

Generic procurement engine for Odoo 19 Community. Industry-agnostic core (base + mail + product).

## Install
`-i advanced_procurement_suite`. Assign **Settings → Users → Procurement**: Requester / Buyer / Manager / Administrator.

## Main flow
Purchase Request → Submit → Review → **Create RFQ Event** → Invite Vendors (creates a draft quote per
vendor) → vendors' quotes are recorded & **submitted** → compare on the scorecard → **Create Award**
(picks the recommended quote or a forced one) → Request Approval → Approve → (Convert to PO via the
purchase add-on). Every state change writes a `procurement.audit.log` row.

## Weighted scoring
Each submitted quote is scored vs its peers in the RFQ: price (lowest = 100), delivery (earliest =
100), quality (from the vendor profile / manual), risk (from the vendor profile risk level). The
weighted total uses `procurement.evaluation.criteria` weights; the RFQ recommends the top quote
(or lowest price if that method is chosen).

## Split award & savings
Award lines map each RFQ line to a quote line with an awarded quantity, so quantities can be split
across vendors (over-award blocked unless `procurement.allow_over_award`). Savings =
estimated_total − awarded_total, computed when the award is approved.

## Vendor performance & contracts
Performance reviews feed the vendor profile's quality/delivery/price/service scores, on-time rate
and average delay. Vendor contracts flip to *expiring_soon* near the renewal/end date and a daily
cron schedules renewal-reminder activities.

## Extending later
`advanced_procurement_purchase` (awards → POs), `_stock`, `_vendor_portal`, `_budget`,
`_contract_ai`, `_approval_workflow` (high-value/risky awards), `_whatsapp`, `_reports`,
`_supplier_compliance`.

## License
LGPL-3.
