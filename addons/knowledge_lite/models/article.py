from odoo import api, fields, models


class Article(models.Model):
    _name = "knowledge.lite.article"
    _description = "Knowledge Article"
    _inherit = ["mail.thread"]
    _parent_store = True
    _order = "sequence, name"

    name = fields.Char(string="Title", required=True, tracking=True)
    body = fields.Html(string="Content", sanitize=False)
    parent_id = fields.Many2one("knowledge.lite.article", string="Parent",
                                index=True, ondelete="cascade")
    parent_path = fields.Char(index=True)
    child_ids = fields.One2many("knowledge.lite.article", "parent_id", string="Sub-articles")
    author_id = fields.Many2one("res.users", default=lambda s: s.env.user)
    is_favorite = fields.Boolean(string="Favorite")
    sequence = fields.Integer(default=10)
    company_id = fields.Many2one("res.company", default=lambda s: s.env.company)
    full_name = fields.Char(compute="_compute_full_name")

    @api.depends("name", "parent_id.full_name")
    def _compute_full_name(self):
        for art in self:
            art.full_name = (
                "%s / %s" % (art.parent_id.full_name, art.name)
                if art.parent_id else art.name)

    def action_toggle_favorite(self):
        for art in self:
            art.is_favorite = not art.is_favorite
