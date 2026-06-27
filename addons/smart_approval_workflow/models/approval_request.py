from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

ADMIN_GROUP = "smart_approval_workflow.group_approval_admin"
TODO_ACTIVITY = "mail.mail_activity_data_todo"


class ApprovalRequest(models.Model):
    _name = "approval.request"
    _description = "Approval Request"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "request_date desc, id desc"

    name = fields.Char(
        string="Reference", required=True, copy=False, readonly=True,
        index=True, default=lambda s: "New")
    workflow_id = fields.Many2one(
        "approval.workflow", string="Workflow", required=True,
        ondelete="restrict", tracking=True)
    res_model = fields.Char(
        related="workflow_id.model_name", store=True, string="Document Model")
    res_id = fields.Integer(string="Document ID")
    resource_ref = fields.Reference(
        selection="_selection_models", string="Document",
        compute="_compute_resource_ref", inverse="_inverse_resource_ref",
        help="The specific document this request is about.")

    requester_id = fields.Many2one(
        "res.users", string="Requester", required=True, tracking=True,
        default=lambda s: s.env.user)
    company_id = fields.Many2one(
        "res.company", string="Company", required=True,
        default=lambda s: s.env.company)
    current_step_id = fields.Many2one(
        "approval.workflow.step", string="Current Step", tracking=True,
        readonly=True)
    state = fields.Selection(
        [("draft", "Draft"),
         ("pending", "Pending"),
         ("approved", "Approved"),
         ("rejected", "Rejected"),
         ("cancelled", "Cancelled")],
        string="Status", default="draft", required=True, tracking=True)

    request_date = fields.Datetime(string="Request Date",
                                   default=fields.Datetime.now)
    approved_date = fields.Datetime(readonly=True, copy=False)
    rejected_date = fields.Datetime(readonly=True, copy=False)

    approval_line_ids = fields.One2many(
        "approval.request.line", "request_id", string="Approval History")
    notes = fields.Text()

    current_approver_ids = fields.Many2many(
        "res.users", string="Current Approvers",
        compute="_compute_current_approvers")
    can_approve = fields.Boolean(compute="_compute_can_approve")
    progress = fields.Char(compute="_compute_progress")

    # ------------------------------------------------------------------ refs
    @api.model
    def _selection_models(self):
        models = self.env["approval.workflow"].sudo().search([]).mapped(
            "model_id")
        return [(m.model, m.name) for m in models if m.model in self.env]

    @api.depends("res_model", "res_id")
    def _compute_resource_ref(self):
        for r in self:
            if r.res_model and r.res_id and r.res_model in self.env:
                r.resource_ref = "%s,%s" % (r.res_model, r.res_id)
            else:
                r.resource_ref = False

    def _inverse_resource_ref(self):
        for r in self:
            if r.resource_ref:
                r.res_id = r.resource_ref.id

    @api.constrains("resource_ref", "workflow_id")
    def _check_resource_model(self):
        for r in self:
            if (r.resource_ref and r.workflow_id
                    and r.resource_ref._name != r.workflow_id.model_name):
                raise ValidationError(
                    "The document must be a '%s'." % r.workflow_id.model_name)

    # ------------------------------------------------------------- computes
    @api.depends("current_step_id", "state", "approval_line_ids.action")
    def _compute_current_approvers(self):
        for r in self:
            if r.state == "pending" and r.current_step_id:
                r.current_approver_ids = r.current_step_id._resolve_approvers(r)
            else:
                r.current_approver_ids = False

    @api.depends("current_approver_ids", "state")
    def _compute_can_approve(self):
        is_admin = self.env.user.has_group(ADMIN_GROUP)
        for r in self:
            r.can_approve = r.state == "pending" and (
                self.env.user in r.current_approver_ids or is_admin)

    @api.depends("current_step_id", "state", "workflow_id.approval_step_ids")
    def _compute_progress(self):
        for r in self:
            steps = r._ordered_steps()
            total = len(steps)
            if r.state == "approved":
                done = total
            elif r.state == "pending" and r.current_step_id in steps:
                done = list(steps).index(r.current_step_id)
            else:
                done = 0
            r.progress = "%s / %s" % (done, total)

    # --------------------------------------------------------------- create
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "approval.request") or "New"
        return super().create(vals_list)

    def _ordered_steps(self):
        self.ensure_one()
        return self.workflow_id.approval_step_ids.filtered("active").sorted(
            "sequence")

    # --------------------------------------------------------------- engine
    def action_submit(self):
        for r in self:
            if r.state != "draft":
                raise UserError("Only draft requests can be submitted.")
            if not r.res_id:
                raise UserError("Link a document before submitting.")
            steps = r._ordered_steps()
            if not steps:
                raise UserError(
                    "Workflow '%s' has no active approval steps."
                    % r.workflow_id.name)
            r.write({"state": "pending",
                     "request_date": fields.Datetime.now()})
            r.message_post(body="Submitted for approval.")
            r._activate_step(steps[0])

    def _activate_step(self, step):
        self.ensure_one()
        self.current_step_id = step
        approvers = step._resolve_approvers(self)
        if not approvers:
            self.message_post(
                body="Step '%s' has no resolvable approver — skipped." % step.name)
            return self._advance_from(step)
        self.env["approval.request.line"].create([{
            "request_id": self.id, "step_id": step.id,
            "approver_id": user.id, "action": "pending",
        } for user in approvers])
        self._schedule_activities(approvers, step)

    def _schedule_activities(self, approvers, step):
        self.ensure_one()
        for user in approvers:
            self.activity_schedule(
                TODO_ACTIVITY, user_id=user.id,
                summary="Approval required: %s" % self.name,
                note="Step '%s' — please review and approve or reject." % step.name)

    def _clear_activities(self):
        self.activity_ids.unlink()

    def _act(self, action, comment=None):
        """Record an approve/reject action by the current user."""
        self.ensure_one()
        if self.state != "pending":
            raise UserError(
                "Only pending requests can be approved or rejected.")
        step = self.current_step_id
        user = self.env.user
        is_admin = user.has_group(ADMIN_GROUP)
        if user not in step._resolve_approvers(self) and not is_admin:
            raise UserError(
                "You are not an approver for the current step.")
        if action == "rejected" and not step.allow_reject:
            raise UserError("Rejection is not allowed at this step.")

        line = self.approval_line_ids.filtered(
            lambda l: l.step_id == step and l.approver_id == user
            and l.action == "pending")[:1]
        if not line:
            line = self.env["approval.request.line"].create({
                "request_id": self.id, "step_id": step.id,
                "approver_id": user.id, "action": "pending"})
        line.write({"action": action,
                    "action_date": fields.Datetime.now(),
                    "comment": comment})

        if action == "rejected":
            self.write({"state": "rejected",
                        "rejected_date": fields.Datetime.now()})
            self._clear_activities()
            self.message_post(
                body="Rejected by %s.%s" % (
                    user.name, " %s" % comment if comment else ""))
            return
        self.message_post(
            body="Approved by %s (step '%s').%s" % (
                user.name, step.name, " %s" % comment if comment else ""))
        approved = len(self.approval_line_ids.filtered(
            lambda l: l.step_id == step and l.action == "approved"))
        if approved >= step.required_approval_count:
            self._advance_from(step)

    def _advance_from(self, step):
        self.ensure_one()
        self._clear_activities()
        steps = list(self._ordered_steps())
        idx = steps.index(step) if step in steps else -1
        nxt = steps[idx + 1] if 0 <= idx < len(steps) - 1 else False
        if nxt:
            self._activate_step(nxt)
        else:
            self.write({"state": "approved",
                        "approved_date": fields.Datetime.now(),
                        "current_step_id": False})
            self.message_post(body="Approval complete.")

    # ----------------------------------------------------------- UI actions
    def action_submit_for_approval(self):
        return self.action_submit()

    def _open_action_wizard(self, action):
        self.ensure_one()
        if not self.can_approve:
            raise UserError("You are not an approver for the current step.")
        return {
            "type": "ir.actions.act_window",
            "name": "Approve" if action == "approved" else "Reject",
            "res_model": "approval.action.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_request_id": self.id,
                        "default_action": action},
        }

    def action_approve(self):
        return self._open_action_wizard("approved")

    def action_reject(self):
        return self._open_action_wizard("rejected")

    def action_cancel(self):
        for r in self:
            if r.state in ("approved", "rejected", "cancelled"):
                raise UserError(
                    "This request can no longer be cancelled.")
            r._clear_activities()
            r.write({"state": "cancelled"})
            r.message_post(body="Cancelled.")

    def action_reset_to_draft(self):
        for r in self:
            if r.state not in ("cancelled", "rejected"):
                raise UserError(
                    "Only cancelled or rejected requests can be reset.")
            r._clear_activities()
            r.approval_line_ids.unlink()
            r.write({"state": "draft", "current_step_id": False,
                     "approved_date": False, "rejected_date": False})

    def action_open_document(self):
        self.ensure_one()
        if not (self.res_model and self.res_id):
            raise UserError("No document is linked to this request.")
        return {
            "type": "ir.actions.act_window",
            "res_model": self.res_model,
            "res_id": self.res_id,
            "view_mode": "form",
            "target": "current",
        }

    # ------------------------------------------------------- integration API
    @api.model
    def create_for_record(self, record, workflow=None):
        """Public helper for optional integration modules: create + submit an
        approval request for an arbitrary document. Returns the request (empty
        recordset if no matching workflow)."""
        if workflow is None:
            candidates = self.env["approval.workflow"].search(
                [("model_name", "=", record._name), ("active", "=", True)])
            workflow = candidates.filtered(lambda w: w._matches(record))[:1]
        if not workflow:
            return self.browse()
        request = self.create({
            "workflow_id": workflow.id, "res_id": record.id})
        request.action_submit()
        return request
