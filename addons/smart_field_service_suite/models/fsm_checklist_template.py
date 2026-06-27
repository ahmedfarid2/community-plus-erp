from odoo import fields, models

ANSWER_TYPES = [
    ("yes_no", "Yes / No"), ("text", "Text"), ("number", "Number"),
    ("photo", "Photo"), ("checkbox", "Checkbox"),
]


class FsmChecklistTemplate(models.Model):
    _name = "fsm.checklist.template"
    _description = "Checklist Template"
    _order = "name"

    name = fields.Char(required=True, translate=True)
    service_type_id = fields.Many2one("fsm.service.type", string="Service Type")
    checklist_item_ids = fields.One2many(
        "fsm.checklist.template.line", "template_id", string="Items", copy=True)
    active = fields.Boolean(default=True)
    notes = fields.Text()


class FsmChecklistTemplateLine(models.Model):
    _name = "fsm.checklist.template.line"
    _description = "Checklist Template Item"
    _order = "sequence, id"

    template_id = fields.Many2one("fsm.checklist.template", required=True,
                                  ondelete="cascade")
    sequence = fields.Integer(default=10)
    name = fields.Char(required=True, translate=True)
    is_required = fields.Boolean(string="Required")
    expected_answer_type = fields.Selection(
        ANSWER_TYPES, string="Answer Type", default="yes_no", required=True)
    notes = fields.Char()
