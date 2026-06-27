from odoo import fields, models


class ProcurementAuditLog(models.Model):
    _name = "procurement.audit.log"
    _description = "Procurement Audit Log"
    _order = "event_date desc, id desc"

    event_type = fields.Selection(
        [("request_created", "Request Created"), ("submitted", "Submitted"),
         ("reviewed", "Reviewed"), ("rfq_opened", "RFQ Opened"),
         ("vendor_invited", "Vendor Invited"),
         ("quote_submitted", "Quote Submitted"),
         ("quote_shortlisted", "Quote Shortlisted"),
         ("quote_rejected", "Quote Rejected"), ("award_created", "Award Created"),
         ("approval_requested", "Approval Requested"),
         ("award_approved", "Award Approved"), ("award_rejected", "Award Rejected"),
         ("po_created", "PO Created"), ("cancelled", "Cancelled"),
         ("note", "Note")], string="Event", required=True)
    event_date = fields.Datetime(default=fields.Datetime.now)
    user_id = fields.Many2one("res.users", default=lambda s: s.env.user)
    related_model = fields.Char()
    related_record_id = fields.Integer()
    reference = fields.Char(string="Reference")
    description = fields.Char()
    notes = fields.Text()


class ProcurementAuditMixin(models.AbstractModel):
    _name = "procurement.audit.mixin"
    _description = "Procurement Audit Mixin"

    def _audit(self, event_type, description=None):
        for rec in self:
            self.env["procurement.audit.log"].create({
                "event_type": event_type,
                "related_model": rec._name, "related_record_id": rec.id,
                "reference": rec.display_name,
                "description": description or "",
            })
