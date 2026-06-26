from odoo import api, fields, models


class Appraisal(models.Model):
    _name = "hr.appraisal.lite"
    _description = "Employee Appraisal"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "appraisal_date desc, id desc"

    name = fields.Char(compute="_compute_name", store=True)
    employee_id = fields.Many2one("hr.employee", required=True, tracking=True)
    manager_id = fields.Many2one("hr.employee", string="Manager", tracking=True)
    department_id = fields.Many2one(related="employee_id.department_id", store=True)
    job_id = fields.Many2one(related="employee_id.job_id", store=True, string="Job Position")
    company_id = fields.Many2one("res.company", default=lambda s: s.env.company)
    appraisal_date = fields.Date(default=fields.Date.context_today, tracking=True)
    state = fields.Selection(
        [("new", "To Start"), ("pending", "Appraisal Sent"),
         ("done", "Done"), ("cancel", "Cancelled")],
        default="new", required=True, tracking=True)
    final_rating = fields.Selection(
        [("below", "Below Expectations"), ("meet", "Meets Expectations"),
         ("exceed", "Exceeds Expectations"), ("strong", "Strongly Exceeds")],
        tracking=True)
    employee_feedback = fields.Html()
    manager_feedback = fields.Html()
    note = fields.Text()

    @api.depends("employee_id", "appraisal_date")
    def _compute_name(self):
        for app in self:
            base = app.employee_id.name or "Appraisal"
            app.name = "%s - %s" % (base, app.appraisal_date) if app.appraisal_date else base

    @api.onchange("employee_id")
    def _onchange_employee_id(self):
        if self.employee_id and self.employee_id.parent_id:
            self.manager_id = self.employee_id.parent_id

    def action_confirm(self):
        for app in self:
            app.state = "pending"
            target = app.manager_id.user_id or app.employee_id.user_id
            if target:
                app.activity_schedule(
                    "mail.mail_activity_data_todo", user_id=target.id,
                    summary="Appraisal: %s" % (app.employee_id.name or ""))

    def action_done(self):
        self.write({"state": "done"})
        self.activity_unlink(["mail.mail_activity_data_todo"])

    def action_cancel(self):
        self.write({"state": "cancel"})

    def action_reset(self):
        self.write({"state": "new"})
