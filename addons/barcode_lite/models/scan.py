from odoo import api, fields, models


class BarcodeSession(models.Model):
    _name = "barcode.lite.session"
    _description = "Barcode Scan Session"
    _order = "create_date desc, id desc"

    name = fields.Char(default="Scan Session", required=True)
    scan_input = fields.Char(
        string="Scan here",
        help="Focus this field and scan — a USB scanner types the barcode + Enter.")
    location_id = fields.Many2one("stock.location", string="Location")
    line_ids = fields.One2many("barcode.lite.line", "session_id", string="Scanned")
    total_qty = fields.Float(compute="_compute_total")
    company_id = fields.Many2one("res.company", default=lambda s: s.env.company)

    def _compute_total(self):
        for s in self:
            s.total_qty = sum(s.line_ids.mapped("quantity"))

    @api.onchange("scan_input")
    def _onchange_scan_input(self):
        """Resolve the scanned barcode to a product and add/increment a line."""
        code = (self.scan_input or "").strip()
        if not code:
            return
        product = self.env["product.product"].search([("barcode", "=", code)], limit=1)
        if not product:
            # Fall back to internal reference so it's still useful without barcodes set.
            product = self.env["product.product"].search(
                [("default_code", "=", code)], limit=1)
        if product:
            line = self.line_ids.filtered(lambda l: l.product_id == product)[:1]
            if line:
                line.quantity += 1
            else:
                self.line_ids = [(0, 0, {"product_id": product.id, "barcode": code,
                                         "quantity": 1})]
        else:
            self.line_ids = [(0, 0, {"barcode": code, "quantity": 1,
                                     "not_found": True})]
        self.scan_input = False  # clear for the next scan


class BarcodeLine(models.Model):
    _name = "barcode.lite.line"
    _description = "Barcode Scan Line"

    session_id = fields.Many2one("barcode.lite.session", ondelete="cascade")
    product_id = fields.Many2one("product.product", string="Product")
    barcode = fields.Char()
    quantity = fields.Float(default=1.0)
    not_found = fields.Boolean()
