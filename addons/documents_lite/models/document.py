from odoo import fields, models


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

    def action_archive_document(self):
        self.write({"state": "archived"})

    def action_activate_document(self):
        self.write({"state": "active"})
