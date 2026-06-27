from odoo import fields, models
from odoo.exceptions import UserError


class SocialAccount(models.Model):
    _name = "social.lite.account"
    _description = "Social Media Account"
    _order = "name"

    name = fields.Char(required=True)
    platform = fields.Selection(
        [("facebook", "Facebook Page"), ("x", "X / Twitter"),
         ("linkedin", "LinkedIn")], default="facebook", required=True)
    target_id = fields.Char(string="Page / Account ID")
    access_token = fields.Char(string="Access Token")
    active = fields.Boolean(default=True)
    company_id = fields.Many2one("res.company", default=lambda s: s.env.company)


class SocialPost(models.Model):
    _name = "social.lite.post"
    _description = "Social Post"
    _inherit = ["mail.thread"]
    _order = "create_date desc, id desc"

    name = fields.Char(string="Title", default="New Post")
    account_ids = fields.Many2many("social.lite.account", string="Publish to",
                                   required=True)
    message = fields.Text(required=True)
    link_url = fields.Char(string="Link")
    state = fields.Selection(
        [("draft", "Draft"), ("posted", "Posted"), ("failed", "Failed")],
        default="draft", required=True, tracking=True)
    result = fields.Text(readonly=True)

    def action_post(self):
        """Publish to each linked account. Facebook uses the Graph API (real);
        other platforms need their own API wiring + the account's token."""
        import requests
        for post in self:
            if not post.account_ids:
                raise UserError("Add at least one account to publish to.")
            logs = []
            ok = True
            for acc in post.account_ids:
                if not acc.access_token:
                    logs.append("%s: missing access token" % acc.name)
                    ok = False
                    continue
                if acc.platform == "facebook":
                    url = "https://graph.facebook.com/%s/feed" % (acc.target_id or "me")
                    payload = {"message": post.message, "access_token": acc.access_token}
                    if post.link_url:
                        payload["link"] = post.link_url
                    try:
                        r = requests.post(url, data=payload, timeout=20)
                        logs.append("%s: HTTP %s %s" % (acc.name, r.status_code, r.text[:120]))
                        ok = ok and r.status_code == 200
                    except Exception as e:  # noqa: BLE001
                        logs.append("%s: %s" % (acc.name, repr(e))); ok = False
                else:
                    # X / LinkedIn: connector point — needs that platform's API call.
                    logs.append("%s: %s API not wired (add credentials + endpoint)"
                                % (acc.name, acc.platform))
                    ok = False
            post.result = "\n".join(logs)
            post.state = "posted" if ok else "failed"
        return True
