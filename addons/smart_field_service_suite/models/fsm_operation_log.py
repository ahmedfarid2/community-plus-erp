from odoo import fields, models


class FsmOperationLog(models.Model):
    _name = "fsm.operation.log"
    _description = "Field Service Operation Log"
    _order = "event_date desc, id desc"

    work_order_id = fields.Many2one("fsm.work.order", string="Work Order",
                                    required=True, ondelete="cascade",
                                    index=True)
    partner_id = fields.Many2one(related="work_order_id.partner_id", store=True)
    event_type = fields.Selection(
        [("created", "Created"), ("scheduled", "Scheduled"),
         ("assigned", "Assigned"), ("dispatched", "Dispatched"),
         ("travel_started", "Travel Started"), ("work_started", "Work Started"),
         ("waiting_parts", "Waiting Parts"),
         ("waiting_customer", "Waiting Customer"),
         ("completed", "Completed"), ("reviewed", "Reviewed"),
         ("cancelled", "Cancelled"), ("sla_warning", "SLA Warning"),
         ("sla_breached", "SLA Breached"), ("note", "Note")],
        string="Event", required=True)
    event_date = fields.Datetime(default=fields.Datetime.now)
    user_id = fields.Many2one("res.users", string="User")
    description = fields.Char()
    notes = fields.Text()
