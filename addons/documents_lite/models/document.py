from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class DocumentFolder(models.Model):
    _name = "documents.lite.folder"
    _description = "Document Folder"
    _parent_store = True
    _order = "parent_path, name"

    name = fields.Char(required=True)
    parent_id = fields.Many2one("documents.lite.folder", index=True, ondelete="cascade")
    parent_path = fields.Char(index=True)
    active = fields.Boolean(default=True)


class Document(models.Model):
    _name = "documents.lite.document"
    _description = "Document"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc, id desc"

    name = fields.Char(required=True, tracking=True)
    folder_id = fields.Many2one("documents.lite.folder", required=True)
    owner_id = fields.Many2one("res.users", default=lambda self: self.env.user)
    partner_id = fields.Many2one("res.partner")
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company)
    document = fields.Binary(attachment=True, required=True)
    filename = fields.Char()
    tag = fields.Char()
    state = fields.Selection(
        [("draft", "Draft"), ("active", "Active"), ("archived", "Archived")],
        default="active",
        required=True,
        tracking=True,
    )
    notes = fields.Text()
    expiry_date = fields.Date(tracking=True,
                              help="Date this document expires (contract, licence, certificate...).")
    reminder_sent = fields.Boolean(default=False, copy=False)
    expiry_state = fields.Selection(
        [("none", "No expiry"), ("valid", "Valid"),
         ("expiring", "Expiring soon"), ("expired", "Expired")],
        compute="_compute_expiry_state", store=True, string="Expiry")

    EXPIRY_WINDOW_DAYS = 30

    @api.depends("expiry_date")
    def _compute_expiry_state(self):
        today = fields.Date.context_today(self)
        for doc in self:
            if not doc.expiry_date:
                doc.expiry_state = "none"
            elif doc.expiry_date < today:
                doc.expiry_state = "expired"
            elif doc.expiry_date <= today + relativedelta(days=doc.EXPIRY_WINDOW_DAYS):
                doc.expiry_state = "expiring"
            else:
                doc.expiry_state = "valid"

    def write(self, vals):
        # A new expiry date should be eligible for a fresh reminder.
        if "expiry_date" in vals and "reminder_sent" not in vals:
            vals["reminder_sent"] = False
        return super().write(vals)

    @api.model
    def _cron_expiry_reminders(self, days_ahead=None):
        """Scheduled: raise a to-do for the owner of each soon-to-expire document."""
        days_ahead = self.EXPIRY_WINDOW_DAYS if days_ahead is None else days_ahead
        today = fields.Date.context_today(self)
        limit = today + relativedelta(days=days_ahead)
        docs = self.search([
            ("state", "!=", "archived"),
            ("expiry_date", "!=", False),
            ("expiry_date", "<=", limit),
            ("reminder_sent", "=", False),
        ])
        for doc in docs:
            user = doc.owner_id or self.env.user
            doc.activity_schedule(
                "mail.mail_activity_data_todo",
                user_id=user.id,
                date_deadline=doc.expiry_date,
                summary="Document expiring: %s (expires %s)" % (doc.name, doc.expiry_date),
            )
            doc.reminder_sent = True
        return len(docs)

    def action_archive_document(self):
        self.write({"state": "archived"})

    def action_activate_document(self):
        self.write({"state": "active"})
