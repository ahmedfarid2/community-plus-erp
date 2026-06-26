from odoo import api, fields, models


class QualityPoint(models.Model):
    _name = "quality.lite.point"
    _description = "Quality Control Point"
    _order = "name"

    name = fields.Char(required=True)
    product_id = fields.Many2one("product.product", string="Product")
    test_type = fields.Selection(
        [("pass_fail", "Pass / Fail"), ("measure", "Measure")],
        default="pass_fail", required=True)
    norm_min = fields.Float(string="Min")
    norm_max = fields.Float(string="Max")
    note = fields.Text(string="Instructions")
    active = fields.Boolean(default=True)


class QualityCheck(models.Model):
    _name = "quality.lite.check"
    _description = "Quality Check"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc, id desc"

    name = fields.Char(compute="_compute_name", store=True)
    point_id = fields.Many2one("quality.lite.point", string="Control Point",
                               required=True)
    product_id = fields.Many2one("product.product", string="Product")
    test_type = fields.Selection(related="point_id.test_type", store=True)
    picking_id = fields.Many2one("stock.picking", string="Transfer")
    measure = fields.Float()
    state = fields.Selection(
        [("todo", "To Do"), ("pass", "Passed"), ("fail", "Failed")],
        default="todo", required=True, tracking=True)
    company_id = fields.Many2one("res.company", default=lambda s: s.env.company)
    note = fields.Text()

    @api.depends("point_id", "product_id")
    def _compute_name(self):
        for chk in self:
            chk.name = "%s / %s" % (chk.point_id.name or "Check",
                                    chk.product_id.display_name or "")

    def action_pass(self):
        self.write({"state": "pass"})

    def action_fail(self):
        for chk in self:
            chk.state = "fail"
            chk.activity_schedule(
                "mail.mail_activity_data_todo", user_id=chk.env.user.id,
                summary="Quality failure: %s" % chk.name)

    def action_measure_check(self):
        """For 'measure' points: pass if within the norm range, else fail."""
        for chk in self:
            pt = chk.point_id
            ok = (pt.norm_min <= chk.measure <= pt.norm_max) if pt.test_type == "measure" else True
            chk.state = "pass" if ok else "fail"
