from odoo import api, fields, models


class HelpdeskBoard(models.TransientModel):
    _name = "helpdesk.lite.board"
    _description = "Helpdesk Dashboard"

    company_id = fields.Many2one("res.company", default=lambda s: s.env.company)
    open_tickets = fields.Integer(compute="_compute_kpis")
    urgent = fields.Integer(compute="_compute_kpis")
    unassigned = fields.Integer(compute="_compute_kpis")
    my_open = fields.Integer(compute="_compute_kpis")
    waiting = fields.Integer(compute="_compute_kpis")
    solved = fields.Integer(compute="_compute_kpis")

    OPEN = [("state", "not in", ("solved", "cancelled"))]

    @api.depends("company_id")
    def _compute_kpis(self):
        T = self.env["helpdesk.lite.ticket"]
        for b in self:
            cdom = [("company_id", "=", b.company_id.id)]
            b.open_tickets = T.search_count(cdom + self.OPEN)
            b.urgent = T.search_count(cdom + self.OPEN + [("priority", "=", "3")])
            b.unassigned = T.search_count(cdom + self.OPEN + [("user_id", "=", False)])
            b.my_open = T.search_count(cdom + self.OPEN + [("user_id", "=", self.env.uid)])
            b.waiting = T.search_count(cdom + [("state", "=", "waiting")])
            b.solved = T.search_count(cdom + [("state", "=", "solved")])

    def _open(self, extra, name):
        # Drill-downs open as a filtered list (the natural view for a KPI
        # click-through); kanban stays available from the Tickets menu.
        return {"type": "ir.actions.act_window", "name": name,
                "res_model": "helpdesk.lite.ticket",
                "domain": [("company_id", "=", self.company_id.id)] + extra,
                "view_mode": "list,form", "target": "current"}

    def action_open(self):
        return self._open(self.OPEN, "Open Tickets")

    def action_urgent(self):
        return self._open(self.OPEN + [("priority", "=", "3")], "Urgent Tickets")

    def action_unassigned(self):
        return self._open(self.OPEN + [("user_id", "=", False)], "Unassigned Tickets")

    def action_mine(self):
        return self._open(self.OPEN + [("user_id", "=", self.env.uid)], "My Tickets")

    def action_refresh(self):
        return {"type": "ir.actions.act_window", "res_model": "helpdesk.lite.board",
                "view_mode": "form", "target": "current"}
