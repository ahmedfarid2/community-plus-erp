from odoo import api, fields, models


class Conversation(models.Model):
    _name = "ai.lite.conversation"
    _description = "AI Conversation"
    _order = "write_date desc, id desc"

    name = fields.Char(default="New chat", required=True)
    user_id = fields.Many2one("res.users", default=lambda s: s.env.user)
    line_ids = fields.One2many("ai.lite.message", "conversation_id", string="Messages")
    prompt = fields.Text(string="Your message")

    def _llm(self, messages):
        """Call the configured LLM. Real HTTP call — works with a running Ollama
        (free, local) or an OpenAI/Anthropic key. Returns the assistant text."""
        import requests
        ICP = self.env["ir.config_parameter"].sudo()
        provider = ICP.get_param("ai_lite.provider", "ollama")
        model = ICP.get_param("ai_lite.model") or (
            "gpt-4o-mini" if provider == "openai" else
            "claude-3-5-haiku-20241022" if provider == "anthropic" else "llama3.2")
        key = ICP.get_param("ai_lite.api_key", "")
        base = ICP.get_param("ai_lite.base_url", "")
        try:
            if provider == "openai":
                r = requests.post((base or "https://api.openai.com/v1") + "/chat/completions",
                                  headers={"Authorization": "Bearer %s" % key},
                                  json={"model": model, "messages": messages}, timeout=60)
                return r.json()["choices"][0]["message"]["content"]
            if provider == "anthropic":
                sys = " ".join(m["content"] for m in messages if m["role"] == "system")
                r = requests.post((base or "https://api.anthropic.com/v1") + "/messages",
                                  headers={"x-api-key": key, "anthropic-version": "2023-06-01"},
                                  json={"model": model, "max_tokens": 1024,
                                        "system": sys or None,
                                        "messages": [m for m in messages if m["role"] != "system"]},
                                  timeout=60)
                return r.json()["content"][0]["text"]
            # Ollama (local, free). host.docker.internal reaches the Mac host.
            r = requests.post((base or "http://host.docker.internal:11434") + "/api/chat",
                              json={"model": model, "messages": messages, "stream": False},
                              timeout=120)
            return r.json()["message"]["content"]
        except Exception as e:  # noqa: BLE001
            return ("⚠ AI backend not reachable. Set the provider/key in "
                    "Settings → AI Assistant (or run Ollama locally). [%s]" % str(e)[:150])

    def action_send(self):
        self.ensure_one()
        if not (self.prompt or "").strip():
            return
        Msg = self.env["ai.lite.message"]
        Msg.create({"conversation_id": self.id, "role": "user", "content": self.prompt})
        if self.name == "New chat":
            self.name = (self.prompt or "")[:40]
        history = [{"role": m.role, "content": m.content} for m in self.line_ids]
        reply = self._llm(history)
        Msg.create({"conversation_id": self.id, "role": "assistant", "content": reply})
        self.prompt = False
        return {"type": "ir.actions.act_window", "res_model": "ai.lite.conversation",
                "res_id": self.id, "view_mode": "form", "target": "current"}


class Message(models.Model):
    _name = "ai.lite.message"
    _description = "AI Message"
    _order = "id"

    conversation_id = fields.Many2one("ai.lite.conversation", ondelete="cascade",
                                      required=True)
    role = fields.Selection(
        [("user", "You"), ("assistant", "Assistant"), ("system", "System")],
        default="user", required=True)
    content = fields.Text(required=True)
