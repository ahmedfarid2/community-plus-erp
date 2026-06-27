# Smart Field Service & Maintenance Suite (smart_field_service_suite)

> Manage field service work orders, technicians, SLAs, spare parts, recurring maintenance, and customer assets inside Odoo Community.

A generic field-service engine for Odoo 19 Community — HVAC, plumbing, electrical,
appliance repair, IT support, telecom, security, pest control, cleaning, equipment
and medical-equipment maintenance. Industry-agnostic core (`base` + `mail` + `product`).

## Install
```bash
docker compose run --rm --no-deps web odoo -d <db> -i smart_field_service_suite --stop-after-init
```
Assign **Settings → Users → Field Service**: Technician / Dispatcher / Manager / Administrator.

## Main flow
Service Request → **Convert to Work Order** → Schedule → Dispatch → Start Travel →
Arrive/Start Work → (Waiting Parts/Customer) → Complete (required checklist enforced) →
customer sign-off → Review. Service history is stored on the asset on completion.

## SLA
Each priority maps to an `fsm.sla.policy` (response/resolution hours). Deadlines are
computed from creation; `sla_status` is on_track → warning (past response) → breached
(past resolution) → completed. An hourly cron flags breaches with a manager activity.

## Maintenance contracts
`next_service_date` + recurrence drive a daily cron that auto-generates work orders
(deduplicated per contract+date) and schedules renewal-reminder activities before the
end date.

## Technician access
Technicians see and edit **only their assigned work orders** (record rules on the work
order and all line/log models), have no access to service requests, and their menus are
scoped — Configuration/Resources are Manager/Admin only.

## Extending later
`smart_fsm_sale`, `_account` (invoice billable work orders), `_inventory`, `_mobile`,
`_portal`, `_website_booking`, `_route_optimization`, `_ai_scheduling`,
`_predictive_maintenance`, `_whatsapp`, `_reports`, `_approval_workflow`, `_subscription`.

## License
LGPL-3.
