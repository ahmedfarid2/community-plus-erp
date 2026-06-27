"""Seed clickable Field Service demo data. Idempotent: skips if work orders
exist. Run via: odoo shell -d <db> < scripts/dev/seed-fsm.py"""
from datetime import datetime, timedelta

AT = env["fsm.asset.type"]; ST = env["fsm.service.type"]; SK = env["fsm.skill"]
SA = env["fsm.service.area"]; SLA = env["fsm.sla.policy"]
TM = env["fsm.team"]; TE = env["fsm.technician"]; LOC = env["fsm.service.location"]
AS = env["fsm.customer.asset"]; SR = env["fsm.service.request"]
WO = env["fsm.work.order"]; MC = env["fsm.maintenance.contract"]
admin = env.ref("base.user_admin")
admin.write({"group_ids": [(4, env.ref(
    "smart_field_service_suite.group_fsm_admin").id)]})


def ensure(model, key, vals):
    rec = model.search([(key, "=", vals[key])], limit=1)
    return rec or model.create(vals)


hvac = ensure(SK, "name", {"name": "HVAC", "code": "HVAC"})
it = ensure(SK, "name", {"name": "IT Support", "code": "IT"})
elec = ensure(SK, "name", {"name": "Electrical", "code": "ELEC"})
ac = ensure(AT, "name", {"name": "AC Unit", "code": "AC"})
srv = ensure(AT, "name", {"name": "Server", "code": "SRV"})
ensure(SA, "name", {"name": "North", "code": "N"})
ensure(SA, "name", {"name": "South", "code": "S"})
repair = ensure(ST, "name", {"name": "Repair", "code": "REP",
                             "default_priority": "2", "skill_ids": [(6, 0, [hvac.id])]})
pm = ensure(ST, "name", {"name": "Preventive Maintenance", "code": "PM",
                         "default_duration_hours": 2.0})
emerg = ensure(ST, "name", {"name": "Emergency Visit", "code": "EMG",
                            "default_priority": "3"})
for name, prio, resp, res in [("Low", "0", 24, 120), ("Medium", "1", 8, 48),
                              ("High", "2", 4, 24), ("Critical", "3", 1, 8)]:
    if not SLA.search([("priority", "=", prio)], limit=1):
        SLA.create({"name": name, "priority": prio,
                    "response_time_hours": resp, "resolution_time_hours": res})

team = ensure(TM, "name", {"name": "Field Team"})
# one technician linked to admin so 'My Work Orders' shows data
t1 = ensure(TE, "name", {"name": "Sam Carter", "team_id": team.id,
                         "user_id": admin.id, "skill_ids": [(6, 0, [hvac.id, elec.id])],
                         "hourly_cost": 35.0})
t2 = ensure(TE, "name", {"name": "Lina Rossi", "team_id": team.id,
                         "skill_ids": [(6, 0, [it.id])], "hourly_cost": 40.0})


def customer(name):
    return env["res.partner"].search([("name", "=", name)], limit=1) \
        or env["res.partner"].search([("is_company", "=", True)], limit=1)


if WO.search_count([]):
    print("work orders already exist — skipping")
else:
    academy = customer("Bright Future Academy")
    clinic = customer("Apex Dental Clinic")
    agency = customer("Nova Software Agency")

    loc1 = LOC.create({"name": "%s — HQ" % academy.name, "partner_id": academy.id,
                       "city": "Springfield"})
    loc2 = LOC.create({"name": "%s — Clinic" % clinic.name, "partner_id": clinic.id})
    a1 = AS.create({"name": "Rooftop AC #1", "partner_id": academy.id,
                    "service_location_id": loc1.id, "asset_type_id": ac.id,
                    "serial_number": "AC-001", "status": "active"})
    a2 = AS.create({"name": "Server Rack A", "partner_id": agency.id,
                    "asset_type_id": srv.id, "serial_number": "SRV-009"})

    # service requests
    SR.create({"partner_id": academy.id, "service_type_id": repair.id,
               "priority": "2", "source": "phone",
               "description": "AC not cooling in classroom B."})
    sr2 = SR.create({"partner_id": clinic.id, "service_type_id": emerg.id,
                     "priority": "3", "source": "whatsapp",
                     "description": "Power failure in operatory 2."})
    sr2.action_convert_to_work_order()

    def make_wo(partner, stype, tech, asset, state, days_old=0, parts=None,
                checklist_done=True):
        vals = {"partner_id": partner.id, "service_type_id": stype.id,
                "technician_id": tech.id, "team_id": team.id,
                "asset_id": asset.id if asset else False,
                "scheduled_start": datetime.now() + timedelta(days=1)}
        if days_old:
            vals["create_date"] = datetime.now() - timedelta(days=days_old)
        wo = WO.create(vals)
        if checklist_done is not None:
            env["fsm.work.order.checklist.line"].create({
                "work_order_id": wo.id, "name": "Safety check",
                "is_required": True, "is_done": checklist_done})
        for desc, qty, c, p in (parts or []):
            env["fsm.work.order.part.line"].create({
                "work_order_id": wo.id, "description": desc, "quantity": qty,
                "unit_cost": c, "unit_price": p})
        return wo

    # scheduled (future)
    make_wo(academy, pm, t1, a1, "draft").action_schedule()
    # in progress
    w = make_wo(agency, repair, t2, a2, "draft")
    w.action_schedule(); w.action_dispatch(); w.action_start_work()
    # completed with parts + time + profit
    w3 = make_wo(academy, repair, t1, a1, "draft",
                 parts=[("Compressor", 1, 100, 180), ("Gas refill", 2, 15, 30)])
    env["fsm.work.order.time.line"].create({
        "work_order_id": w3.id, "technician_id": t1.id, "time_type": "work",
        "start_time": datetime.now() - timedelta(hours=3),
        "end_time": datetime.now() - timedelta(hours=1)})
    w3.action_schedule(); w3.action_dispatch(); w3.action_start_work()
    w3.action_complete()
    # an old high-priority order to show SLA breach
    make_wo(clinic, emerg, t1, None, "draft", days_old=5).action_schedule()

    # maintenance contract (active) -> generate a work order
    mc = MC.create({"partner_id": academy.id, "service_location_id": loc1.id,
                    "asset_ids": [(6, 0, [a1.id])], "service_type_id": pm.id,
                    "assigned_team_id": team.id, "assigned_technician_id": t1.id,
                    "recurrence_frequency": "quarterly",
                    "contract_end_date": (datetime.now() + timedelta(days=365)).date()})
    mc.action_activate()
    mc.action_generate_next_work_order()

    # refresh SLA statuses
    WO._cron_check_sla()
    print("created %s work orders, %s requests, %s contracts" % (
        WO.search_count([]), SR.search_count([]), MC.search_count([])))

env.cr.commit()
print("WO by state:", {s: WO.search_count([("state", "=", s)])
                       for s in ("draft", "scheduled", "in_progress",
                                 "completed", "reviewed")},
      "| SLA breached:", WO.search_count([("sla_status", "=", "breached")]))
