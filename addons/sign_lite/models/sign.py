from odoo import api, fields, models


class SignRequest(models.Model):
    _name = "sign.lite.request"
    _description = "Signature Request"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc, id desc"

    name = fields.Char(string="Document Name", required=True, tracking=True)
    document = fields.Binary(string="Document", attachment=True)
    filename = fields.Char()
    partner_id = fields.Many2one("res.partner", string="Signer", required=True,
                                 tracking=True)
    company_id = fields.Many2one("res.company", default=lambda s: s.env.company)
    state = fields.Selection(
        [("draft", "Draft"), ("sent", "Sent"),
         ("signed", "Signed"), ("cancel", "Cancelled")],
        default="draft", required=True, tracking=True)
    signature = fields.Binary(string="Signature", copy=False)
    signed_by = fields.Char(copy=False)
    signed_date = fields.Datetime(copy=False, tracking=True)
    note = fields.Text()

    def action_send(self):
        for req in self:
            req.state = "sent"
            user = req.partner_id.user_ids[:1]
            if user:
                req.activity_schedule(
                    "mail.mail_activity_data_todo", user_id=user.id,
                    summary="Signature requested: %s" % req.name)
            req.message_post(body="Signature request sent to %s." % req.partner_id.name)

    def action_sign(self):
        for req in self:
            if not req.signature:
                from odoo.exceptions import UserError
                raise UserError("Draw or upload a signature before confirming.")
            req.write({
                "state": "signed",
                "signed_by": req.partner_id.name,
                "signed_date": fields.Datetime.now(),
            })
            req.activity_unlink(["mail.mail_activity_data_todo"])
            req.message_post(body="Document signed by %s." % req.partner_id.name)

    def action_cancel(self):
        self.write({"state": "cancel"})

    def action_reset(self):
        self.write({"state": "draft", "signature": False,
                    "signed_by": False, "signed_date": False})
