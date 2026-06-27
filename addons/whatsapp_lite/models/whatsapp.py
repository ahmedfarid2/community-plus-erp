from odoo import fields, models
from odoo.exceptions import UserError


class WhatsappAccount(models.Model):
    _name = "whatsapp.lite.account"
    _description = "WhatsApp Business Account"
    _order = "name"

    name = fields.Char(required=True)
    phone_number_id = fields.Char(string="Phone Number ID",
                                  help="From Meta WhatsApp Business / Cloud API.")
    access_token = fields.Char(string="Access Token",
                               help="Permanent token from your Meta app.")
    api_version = fields.Char(default="v18.0", required=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one("res.company", default=lambda s: s.env.company)


class WhatsappMessage(models.Model):
    _name = "whatsapp.lite.message"
    _description = "WhatsApp Message"
    _inherit = ["mail.thread"]
    _order = "create_date desc, id desc"

    account_id = fields.Many2one("whatsapp.lite.account", required=True)
    partner_id = fields.Many2one("res.partner", string="Recipient")
    to_number = fields.Char(string="To (E.164)",
                            help="e.g. +14155550123 — overrides the partner phone.")
    body = fields.Text(required=True)
    state = fields.Selection(
        [("draft", "Draft"), ("sent", "Sent"), ("failed", "Failed")],
        default="draft", required=True, tracking=True)
    provider_message_id = fields.Char(readonly=True)
    error = fields.Text(readonly=True)

    def _recipient(self):
        self.ensure_one()
        num = self.to_number or (self.partner_id.mobile or self.partner_id.phone)
        return (num or "").replace(" ", "").replace("-", "")

    def action_send(self):
        """Send via the WhatsApp Cloud API. Real call — needs a valid token."""
        import requests
        for msg in self:
            acc = msg.account_id
            if not acc.access_token or not acc.phone_number_id:
                raise UserError("Set the Access Token and Phone Number ID on the "
                                "WhatsApp account first (Configuration → Accounts).")
            to = msg._recipient()
            if not to:
                raise UserError("No recipient number (set To or the partner's mobile).")
            url = "https://graph.facebook.com/%s/%s/messages" % (
                acc.api_version, acc.phone_number_id)
            try:
                resp = requests.post(
                    url,
                    headers={"Authorization": "Bearer %s" % acc.access_token},
                    json={"messaging_product": "whatsapp", "to": to.lstrip("+"),
                          "type": "text", "text": {"body": msg.body}},
                    timeout=20)
                data = resp.json()
                if resp.status_code == 200:
                    msg.state = "sent"
                    msg.provider_message_id = (data.get("messages") or [{}])[0].get("id")
                    msg.error = False
                else:
                    msg.state = "failed"
                    msg.error = str(data)
            except Exception as e:  # noqa: BLE001 - network/credentials issue
                msg.state = "failed"
                msg.error = repr(e)
        return True
