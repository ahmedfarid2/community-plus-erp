import base64
import io
import re
from datetime import datetime

from odoo import fields, models
from odoo.exceptions import UserError


class OcrDocument(models.Model):
    _name = "ocr.lite.document"
    _description = "OCR Document"
    _inherit = ["mail.thread"]
    _order = "create_date desc, id desc"

    name = fields.Char(default="New OCR Document", required=True)
    document = fields.Binary(string="Scan / PDF", attachment=True, required=True)
    filename = fields.Char()
    extracted_text = fields.Text(readonly=True)
    amount = fields.Float(string="Detected Total", readonly=True)
    invoice_date = fields.Date(string="Detected Date", readonly=True)
    partner_name = fields.Char(string="Detected Vendor", readonly=True)
    partner_id = fields.Many2one("res.partner", string="Vendor")
    move_id = fields.Many2one("account.move", string="Vendor Bill", readonly=True)
    state = fields.Selection(
        [("draft", "Draft"), ("scanned", "Scanned"), ("billed", "Billed")],
        default="draft", required=True, tracking=True)
    company_id = fields.Many2one("res.company", default=lambda s: s.env.company)

    # ── OCR ─────────────────────────────────────────────────────────────────
    def action_extract(self):
        try:
            import pytesseract  # noqa: F401
            from PIL import Image  # noqa: F401
        except ImportError:
            raise UserError("OCR libraries (pytesseract/Pillow) are not installed "
                            "in this Odoo image.")
        for doc in self:
            if not doc.document:
                raise UserError("Upload a document first.")
            data = base64.b64decode(doc.document)
            text = doc._ocr_bytes(data, doc.filename or "")
            doc.extracted_text = text
            doc._parse(text)
            doc.state = "scanned"

    def _ocr_bytes(self, data, filename):
        import pytesseract
        from PIL import Image
        if filename.lower().endswith(".pdf") or data[:5] == b"%PDF-":
            from pdf2image import convert_from_bytes
            pages = convert_from_bytes(data, dpi=200)
            return "\n".join(pytesseract.image_to_string(p) for p in pages)
        return pytesseract.image_to_string(Image.open(io.BytesIO(data)))

    def _parse(self, text):
        self.ensure_one()
        # Amount: take the largest money-looking number.
        nums = []
        for raw in re.findall(r"\d{1,3}(?:[,\s]\d{3})*\.\d{2}|\d+\.\d{2}", text):
            try:
                nums.append(float(raw.replace(",", "").replace(" ", "")))
            except ValueError:
                pass
        if nums:
            self.amount = max(nums)
        # Date.
        m = re.search(r"\d{4}-\d{2}-\d{2}", text) or re.search(r"\d{2}/\d{2}/\d{4}", text)
        if m:
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
                try:
                    self.invoice_date = datetime.strptime(m.group(0), fmt).date()
                    break
                except ValueError:
                    pass
        # Vendor: first meaningful line.
        for line in text.splitlines():
            if len(line.strip()) > 2:
                self.partner_name = line.strip()[:60]
                break
        if self.partner_name:
            p = self.env["res.partner"].search(
                [("name", "ilike", self.partner_name)], limit=1)
            if p:
                self.partner_id = p

    # ── Create draft vendor bill ────────────────────────────────────────────
    def action_create_bill(self):
        self.ensure_one()
        if not self.amount:
            raise UserError("No amount detected — review the extracted text first.")
        partner = self.partner_id
        if not partner and self.partner_name:
            partner = self.env["res.partner"].create(
                {"name": self.partner_name, "supplier_rank": 1})
        journal = self.env["account.journal"].search(
            [("type", "=", "purchase"), ("company_id", "=", self.company_id.id)], limit=1)
        move = self.env["account.move"].create({
            "move_type": "in_invoice",
            "partner_id": partner.id if partner else False,
            "invoice_date": self.invoice_date or fields.Date.context_today(self),
            "journal_id": journal.id if journal else False,
            "invoice_line_ids": [(0, 0, {
                "name": self.name or "OCR import",
                "quantity": 1, "price_unit": self.amount})],
        })
        self.move_id = move.id
        self.state = "billed"
        return {"type": "ir.actions.act_window", "res_model": "account.move",
                "res_id": move.id, "view_mode": "form", "target": "current"}
