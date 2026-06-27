from odoo import fields, models


class ProcurementEvaluationCriteria(models.Model):
    _name = "procurement.evaluation.criteria"
    _description = "Procurement Evaluation Criteria"
    _order = "name"

    name = fields.Char(required=True, translate=True)
    code = fields.Selection(
        [("price", "Price"), ("delivery", "Delivery Time"),
         ("quality", "Quality"), ("risk", "Vendor Risk"),
         ("payment", "Payment Terms"), ("performance", "Past Performance")],
        required=True, help="Which score this weight applies to.")
    weight_percent = fields.Float(string="Weight (%)", default=20.0)
    active = fields.Boolean(default=True)
    notes = fields.Text()

    _code_uniq = models.Constraint("unique(code)",
                                   "One weight per criterion code.")
