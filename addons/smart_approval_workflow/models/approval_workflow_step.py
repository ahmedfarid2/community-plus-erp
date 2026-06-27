from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ApprovalWorkflowStep(models.Model):
    _name = "approval.workflow.step"
    _description = "Approval Workflow Step"
    _order = "sequence, id"

    workflow_id = fields.Many2one(
        "approval.workflow", string="Workflow", required=True,
        ondelete="cascade", index=True)
    sequence = fields.Integer(default=10)
    name = fields.Char(string="Step Name", required=True, translate=True)
    approver_type = fields.Selection(
        [("user", "Specific User"),
         ("group", "User Group"),
         ("manager", "Requester's Manager")],
        string="Approver", default="user", required=True,
        help="Who approves this step. 'Requester's Manager' uses the HR "
             "reporting line when the HR app is installed.")
    approver_user_id = fields.Many2one("res.users", string="Approver User")
    approver_group_id = fields.Many2one("res.groups", string="Approver Group")
    required_approval_count = fields.Integer(
        string="Required Approvals", default=1, required=True,
        help="How many approvals from this step are needed before moving on "
             "(useful for group steps).")
    allow_reject = fields.Boolean(
        string="Allow Reject", default=True,
        help="Whether an approver may reject the request at this step.")
    escalation_days = fields.Integer(
        string="Escalate After (days)", default=0,
        help="If the step stays pending this many days, send a reminder to the "
             "approvers (and to the escalation user, if set). 0 disables it.")
    escalation_user_id = fields.Many2one(
        "res.users", string="Escalate To",
        help="Optional user notified when the step is overdue.")
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        related="workflow_id.company_id", store=True)

    @api.constrains("approver_type", "approver_user_id", "approver_group_id")
    def _check_approver(self):
        for step in self:
            if step.approver_type == "user" and not step.approver_user_id:
                raise ValidationError(
                    "Step '%s': select an Approver User." % step.name)
            if step.approver_type == "group" and not step.approver_group_id:
                raise ValidationError(
                    "Step '%s': select an Approver Group." % step.name)

    @api.constrains("required_approval_count")
    def _check_count(self):
        for step in self:
            if step.required_approval_count < 1:
                raise ValidationError(
                    "Step '%s': Required Approvals must be at least 1."
                    % step.name)

    def _resolve_approvers(self, request):
        """Return the res.users who may approve this step for a request."""
        self.ensure_one()
        if self.approver_type == "user":
            return self.approver_user_id
        if self.approver_type == "group":
            # all_user_ids includes members via group implication (Odoo 19
            # renamed res.groups.users -> user_ids / all_user_ids).
            return self.approver_group_id.sudo().all_user_ids.filtered("active")
        if self.approver_type == "manager":
            return self._manager_users(request.requester_id)
        return self.env["res.users"]

    def _manager_users(self, user):
        """Best-effort manager resolution via the HR hierarchy when present.
        Keeps the core dependency-light (base + mail) — HR is optional."""
        if "hr.employee" in self.env:
            emp = self.env["hr.employee"].sudo().search(
                [("user_id", "=", user.id)], limit=1)
            if emp and emp.parent_id and emp.parent_id.user_id:
                return emp.parent_id.user_id
        return self.env["res.users"]
