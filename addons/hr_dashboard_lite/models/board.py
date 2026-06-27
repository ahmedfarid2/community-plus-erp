from odoo import api, fields, models


class HrBoard(models.TransientModel):
    _name = "hr.dashboard.lite.board"
    _description = "HR Dashboard"

    company_id = fields.Many2one("res.company", default=lambda s: s.env.company)

    employees = fields.Integer(compute="_compute_kpis")
    departments = fields.Integer(compute="_compute_kpis")
    jobs_open = fields.Integer(compute="_compute_kpis")
    new_hires_30 = fields.Integer(compute="_compute_kpis")
    on_leave_today = fields.Integer(compute="_compute_kpis")
    leave_to_approve = fields.Integer(compute="_compute_kpis")
    applicants = fields.Integer(compute="_compute_kpis")
    expenses_to_approve = fields.Integer(compute="_compute_kpis")

    @api.depends("company_id")
    def _compute_kpis(self):
        from datetime import timedelta
        today = fields.Date.context_today(self)
        env = self.env
        for b in self:
            cdom = [("company_id", "=", b.company_id.id)]
            Emp = env["hr.employee"]
            b.employees = Emp.search_count(cdom)
            b.departments = env["hr.department"].search_count(cdom)
            b.jobs_open = (env["hr.job"].search_count(
                cdom + [("no_of_recruitment", ">", 0)]) if "hr.job" in env else 0)
            b.new_hires_30 = Emp.search_count(
                cdom + [("create_date", ">=", today - timedelta(days=30))])
            if "hr.leave" in env:
                b.on_leave_today = env["hr.leave"].search_count(
                    [("state", "=", "validate"),
                     ("date_from", "<=", today), ("date_to", ">=", today)])
                b.leave_to_approve = env["hr.leave"].search_count(
                    [("state", "in", ("confirm", "validate1"))])
            else:
                b.on_leave_today = b.leave_to_approve = 0
            b.applicants = (env["hr.applicant"].search_count(
                [("active", "=", True)]) if "hr.applicant" in env else 0)
            b.expenses_to_approve = (env["hr.expense.sheet"].search_count(
                cdom + [("state", "=", "submit")])
                if "hr.expense.sheet" in env else 0)

    # --- drill-downs ---
    def _open(self, model, domain, name, views="list,form"):
        return {"type": "ir.actions.act_window", "name": name, "res_model": model,
                "domain": domain, "view_mode": views, "target": "current"}

    def action_employees(self):
        return self._open("hr.employee",
                          [("company_id", "=", self.company_id.id)],
                          "Employees", "kanban,list,form")

    def action_jobs(self):
        return self._open("hr.job", [("no_of_recruitment", ">", 0)], "Open Positions")

    def action_on_leave(self):
        today = fields.Date.context_today(self)
        return self._open("hr.leave",
                          [("state", "=", "validate"),
                           ("date_from", "<=", today), ("date_to", ">=", today)],
                          "On Leave Today")

    def action_leave_approve(self):
        return self._open("hr.leave",
                          [("state", "in", ("confirm", "validate1"))],
                          "Time Off to Approve")

    def action_applicants(self):
        return self._open("hr.applicant", [("active", "=", True)],
                          "Applicants", "kanban,list,form")

    def action_expenses(self):
        return self._open("hr.expense.sheet", [("state", "=", "submit")],
                          "Expense Reports to Approve")

    def action_refresh(self):
        return {"type": "ir.actions.act_window",
                "res_model": "hr.dashboard.lite.board",
                "view_mode": "form", "target": "current"}
