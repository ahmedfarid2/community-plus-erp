from odoo import api, fields, models


class Campaign(models.Model):
    _name = "marketing.lite.campaign"
    _description = "Marketing Campaign"
    _inherit = ["mail.thread"]
    _order = "name"

    name = fields.Char(required=True, tracking=True)
    domain = fields.Char(default="[]", help="Filter on contacts to enroll.")
    state = fields.Selection(
        [("draft", "Draft"), ("running", "Running"), ("stopped", "Stopped")],
        default="draft", required=True, tracking=True)
    activity_ids = fields.One2many("marketing.lite.activity", "campaign_id",
                                   string="Workflow")
    participant_ids = fields.One2many("marketing.lite.participant", "campaign_id")
    participant_count = fields.Integer(compute="_compute_counts")
    activity_count = fields.Integer(compute="_compute_counts")

    def _compute_counts(self):
        for camp in self:
            camp.participant_count = len(camp.participant_ids)
            camp.activity_count = len(camp.activity_ids)

    def action_start(self):
        """Enrol matching contacts as participants and run the campaign."""
        Partner = self.env["res.partner"]
        for camp in self:
            domain = camp._eval_domain()
            existing = camp.participant_ids.mapped("partner_id").ids
            partners = Partner.search(domain + [("id", "not in", existing)])
            self.env["marketing.lite.participant"].create([
                {"campaign_id": camp.id, "partner_id": p.id} for p in partners])
            camp.state = "running"

    def action_stop(self):
        self.write({"state": "stopped"})

    def action_reset(self):
        self.write({"state": "draft"})

    def _eval_domain(self):
        self.ensure_one()
        try:
            from odoo.tools.safe_eval import safe_eval
            dom = safe_eval(self.domain or "[]")
            return dom if isinstance(dom, list) else []
        except Exception:  # noqa: BLE001
            return []


class CampaignActivity(models.Model):
    _name = "marketing.lite.activity"
    _description = "Campaign Activity"
    _order = "sequence, id"

    sequence = fields.Integer(default=10)
    campaign_id = fields.Many2one("marketing.lite.campaign", ondelete="cascade",
                                  required=True)
    name = fields.Char(required=True)
    activity_type = fields.Selection(
        [("email", "Send Email"), ("todo", "To-Do Activity"), ("sms", "Send SMS")],
        default="email", required=True)
    trigger_type = fields.Selection(
        [("begin", "At campaign start"), ("after_prev", "After previous step")],
        default="begin", required=True)
    interval_number = fields.Integer(default=0)
    interval_unit = fields.Selection(
        [("hours", "Hours"), ("days", "Days"), ("weeks", "Weeks")],
        default="days", required=True)


class CampaignParticipant(models.Model):
    _name = "marketing.lite.participant"
    _description = "Campaign Participant"
    _order = "id desc"

    campaign_id = fields.Many2one("marketing.lite.campaign", ondelete="cascade",
                                  required=True)
    partner_id = fields.Many2one("res.partner", string="Contact", required=True)
    state = fields.Selection(
        [("running", "Running"), ("completed", "Completed"), ("unsubscribed", "Unsubscribed")],
        default="running", required=True)
