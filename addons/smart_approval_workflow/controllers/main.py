from odoo import http
from odoo.http import request
from odoo.tools import consteq


class ApprovalPortal(http.Controller):
    """Token-secured approve/reject without logging in.

    The link emailed to an approver carries a per-line secret token. The GET
    page shows the request and Approve/Reject buttons; the POST records the
    action as that line's approver. The token is the authentication, so no
    login is required and CSRF is disabled for this token-scoped endpoint.
    """

    def _resolve_line(self, line_id, token):
        line = request.env["approval.request.line"].sudo().browse(
            line_id).exists()
        if not line or not token or not line.access_token:
            return None
        if not consteq(line.access_token, token):
            return None
        return line

    @staticmethod
    def _is_actionable(line):
        req = line.request_id
        return (req.state == "pending" and line.action == "pending"
                and line.step_id == req.current_step_id)

    @http.route("/approval/act/<int:line_id>", type="http", auth="public",
                methods=["GET", "POST"], csrf=False, website=False)
    def approval_act(self, line_id, token=None, **post):
        line = self._resolve_line(line_id, token)
        if not line:
            return request.render(
                "smart_approval_workflow.portal_invalid", {})
        req = line.request_id

        if request.httprequest.method == "POST":
            if not self._is_actionable(line):
                return request.render(
                    "smart_approval_workflow.portal_done",
                    {"req": req, "result": "handled"})
            action = post.get("action")
            comment = (post.get("comment") or "").strip()
            if action not in ("approved", "rejected"):
                return request.render(
                    "smart_approval_workflow.portal_act",
                    {"line": line, "req": req,
                     "error": "Please choose Approve or Reject."})
            if action == "rejected" and not comment:
                return request.render(
                    "smart_approval_workflow.portal_act",
                    {"line": line, "req": req,
                     "error": "Please give a reason for the rejection."})
            req.sudo()._act(action, comment, approver=line.approver_id)
            return request.render(
                "smart_approval_workflow.portal_done",
                {"req": req, "result": action})

        return request.render(
            "smart_approval_workflow.portal_act",
            {"line": line, "req": req, "error": None,
             "handled": not self._is_actionable(line)})
