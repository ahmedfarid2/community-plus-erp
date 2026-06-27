import ast

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ApprovalWorkflow(models.Model):
    _name = "approval.workflow"
    _description = "Approval Workflow"
    _order = "sequence, name"

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    model_id = fields.Many2one(
        "ir.model", string="Document Model", required=True, ondelete="cascade",
        help="The Odoo document type this workflow approves "
             "(e.g. Purchase Order, Invoice, Expense).")
    model_name = fields.Char(related="model_id.model", store=True,
                             string="Model Name")
    company_id = fields.Many2one(
        "res.company", string="Company", default=lambda s: s.env.company)
    active = fields.Boolean(default=True)

    condition_type = fields.Selection(
        [("always", "Always"),
         ("amount_based", "Amount-based"),
         ("domain_based", "Domain-based")],
        string="Applies When", default="always", required=True,
        help="When this workflow should apply to a document.")
    domain_filter = fields.Char(
        string="Domain", default="[]",
        help="For domain-based workflows: the document must match this domain.")
    amount_field_id = fields.Many2one(
        "ir.model.fields", string="Amount Field",
        domain="[('model_id', '=', model_id), "
               "('ttype', 'in', ['float', 'monetary'])]",
        ondelete="cascade",
        help="For amount-based workflows: the numeric field compared against "
             "the minimum amount. Chosen from the document model's fields to "
             "avoid typos.")
    minimum_amount = fields.Float(
        string="Minimum Amount",
        help="Workflow applies when the amount field is greater than or equal "
             "to this value.")

    approval_step_ids = fields.One2many(
        "approval.workflow.step", "workflow_id", string="Approval Steps",
        copy=True)
    step_count = fields.Integer(compute="_compute_counts")
    request_count = fields.Integer(compute="_compute_counts")
    notes = fields.Text()

    @api.depends("approval_step_ids")
    def _compute_counts(self):
        request_data = {}
        if self.ids:
            groups = self.env["approval.request"]._read_group(
                [("workflow_id", "in", self.ids)],
                ["workflow_id"], ["__count"])
            request_data = {wf.id: count for wf, count in groups}
        for wf in self:
            wf.step_count = len(wf.approval_step_ids)
            wf.request_count = request_data.get(wf.id, 0)

    @api.constrains("domain_filter", "condition_type")
    def _check_domain(self):
        for wf in self:
            if wf.condition_type == "domain_based":
                try:
                    parsed = ast.literal_eval(wf.domain_filter or "[]")
                    assert isinstance(parsed, list)
                except Exception:
                    raise ValidationError(
                        "The Domain on '%s' is not a valid Odoo domain list."
                        % wf.name)

    @api.constrains("condition_type", "amount_field_id")
    def _check_amount(self):
        for wf in self:
            if wf.condition_type == "amount_based" and not wf.amount_field_id:
                raise ValidationError(
                    "Select an Amount Field for the amount-based workflow '%s'."
                    % wf.name)

    def _matches(self, record):
        """Return True if this workflow applies to the given document record."""
        self.ensure_one()
        if record._name != self.model_name:
            return False
        if self.condition_type == "amount_based":
            field = self.amount_field_id.name
            if field not in record._fields:
                return False
            return (record[field] or 0.0) >= self.minimum_amount
        if self.condition_type == "domain_based":
            domain = ast.literal_eval(self.domain_filter or "[]")
            return bool(record.filtered_domain(domain))
        return True

    def action_view_requests(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Approval Requests",
            "res_model": "approval.request",
            "view_mode": "list,form",
            "domain": [("workflow_id", "=", self.id)],
            "context": {"default_workflow_id": self.id},
        }
