# Advanced Warehouse & Inventory Optimization Suite (advanced_inventory_optimization)

> Optimize inventory levels, reorder decisions, stock alerts, warehouse visibility, and slow-moving stock inside Odoo Community.

Generic inventory-optimization engine for Odoo 19 Community (base + mail + product + stock, read-only).

## Install
`-i advanced_inventory_optimization`. Assign **Settings → Users → Inventory Optimization**: User / Manager / Administrator.

## Stock health analysis
**Inventory Optimization → Run Analysis** (or the daily cron) calls
`inventory.stock.health._run_analysis()`: for each storable product × warehouse it matches an
optimization rule, reads stock (qty/forecast/incoming/outgoing) and done outgoing moves over the
analysis window, and upserts a stock-health record. The expensive stock reads happen here; the
derived metrics below are cheap stored computes.

## Reorder calculation
- average_daily_demand = outgoing-to-customer qty over the period / period days
- stock_coverage_days = qty_available / average_daily_demand
- safety_stock = average_daily_demand × safety_stock_days
- reorder_point = average_daily_demand × lead_time + safety_stock
- suggested_qty = max(0, average_daily_demand × (lead_time + min_coverage) + safety_stock −
  (qty_available + incoming)), rounded by the rule's method

## Detection
- **stockout_risk**: critical if forecast < 0 or coverage < lead time; high if coverage < lead +
  safety days; then medium/low/none
- **overstock_risk**: high if coverage > max coverage days
- **movement_status**: dead_stock (no movement > dead_stock_days), slow_moving (> slow_moving_days),
  fast_moving (coverage < min), else normal
- **negative stock** → critical alert
- **health_score** (0-100) from the above

## Alerts & recommendations
The analysis creates de-duplicated open alerts (one per product/warehouse/type) and, for high/critical
stockout risk with a positive suggested qty, a reorder recommendation (no duplicate active one). Crit
alerts can spawn manager activities.

## Extending later
`advanced_inventory_purchase` (approved reorders → POs), `advanced_inventory_procurement` (→ RFQ via
the Procurement suite), `_barcode`, `_ai_forecast`, `_mrp`, `_expiry_lot`, `_accounting`, `_reports`,
`_approval_workflow` (high-value reorders / write-offs), `_whatsapp`.

## License
LGPL-3.
