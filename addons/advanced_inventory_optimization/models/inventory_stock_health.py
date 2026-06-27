from datetime import timedelta

from odoo import api, fields, models


class InventoryStockHealth(models.Model):
    _name = "inventory.stock.health"
    _description = "Inventory Stock Health"
    _inherit = ["mail.thread", "inventory.log.mixin"]
    _order = "health_score, id"
    _rec_name = "product_id"

    product_id = fields.Many2one("product.product", required=True, index=True)
    warehouse_id = fields.Many2one("stock.warehouse", index=True)
    company_id = fields.Many2one("res.company", default=lambda s: s.env.company)
    rule_id = fields.Many2one("inventory.optimization.rule", readonly=True)

    # Stored base figures written by the analysis (the costly part).
    qty_available = fields.Float(readonly=True)
    forecasted_qty = fields.Float(readonly=True)
    incoming_qty = fields.Float(readonly=True)
    outgoing_qty = fields.Float(readonly=True)
    average_daily_demand = fields.Float(readonly=True)
    last_movement_date = fields.Date(readonly=True)
    last_computed_date = fields.Datetime(readonly=True)
    days_without_movement = fields.Integer(compute="_compute_derived", store=True)

    # Cheap derived metrics.
    stock_coverage_days = fields.Float(compute="_compute_derived", store=True)
    safety_stock_qty = fields.Float(compute="_compute_derived", store=True)
    reorder_point_qty = fields.Float(compute="_compute_derived", store=True)
    suggested_reorder_qty = fields.Float(compute="_compute_derived", store=True)
    stockout_risk = fields.Selection(
        [("none", "None"), ("low", "Low"), ("medium", "Medium"),
         ("high", "High"), ("critical", "Critical")],
        compute="_compute_derived", store=True, index=True)
    overstock_risk = fields.Selection(
        [("none", "None"), ("low", "Low"), ("medium", "Medium"),
         ("high", "High")], compute="_compute_derived", store=True, index=True)
    movement_status = fields.Selection(
        [("fast_moving", "Fast Moving"), ("normal", "Normal"),
         ("slow_moving", "Slow Moving"), ("dead_stock", "Dead Stock")],
        compute="_compute_derived", store=True, index=True)
    health_score = fields.Float(compute="_compute_derived", store=True)
    is_ignored = fields.Boolean(default=False)
    state = fields.Selection(
        [("healthy", "Healthy"), ("warning", "Warning"),
         ("critical", "Critical"), ("ignored", "Ignored")],
        compute="_compute_derived", store=True, index=True)
    notes = fields.Text()

    _prod_wh_uniq = models.Constraint(
        "unique(product_id, warehouse_id, company_id)",
        "A stock-health record already exists for this product/warehouse.")

    # ----------------------------------------------------------- derived
    @api.depends("qty_available", "forecasted_qty", "incoming_qty",
                 "average_daily_demand", "last_movement_date", "rule_id",
                 "rule_id.safety_stock_days", "rule_id.default_supplier_lead_time_days",
                 "rule_id.minimum_stock_coverage_days",
                 "rule_id.maximum_stock_coverage_days", "rule_id.slow_moving_days",
                 "rule_id.dead_stock_days", "is_ignored")
    def _compute_derived(self):
        today = fields.Date.context_today(self)
        for h in self:
            rule = h.rule_id
            adv = h.average_daily_demand or 0.0
            qty = h.qty_available or 0.0
            lead = (rule.default_supplier_lead_time_days if rule else 7)
            safety_days = (rule.safety_stock_days if rule else 7)
            min_cov = (rule.minimum_stock_coverage_days if rule else 14)
            max_cov = (rule.maximum_stock_coverage_days if rule else 120)
            slow_days = (rule.slow_moving_days if rule else 90)
            dead_days = (rule.dead_stock_days if rule else 180)

            h.days_without_movement = (today - h.last_movement_date).days \
                if h.last_movement_date else 9999
            h.stock_coverage_days = (qty / adv) if adv > 0 else (
                9999.0 if qty > 0 else 0.0)
            h.safety_stock_qty = adv * safety_days
            h.reorder_point_qty = adv * lead + h.safety_stock_qty
            order_up_to = adv * (lead + min_cov) + h.safety_stock_qty
            raw = max(0.0, order_up_to - (qty + (h.incoming_qty or 0.0)))
            h.suggested_reorder_qty = rule._round_qty(raw) if rule else round(raw)

            cov = h.stock_coverage_days
            # stockout risk
            if (h.forecasted_qty or 0.0) < 0 or (adv > 0 and cov < lead):
                h.stockout_risk = "critical"
            elif adv > 0 and cov < lead + safety_days:
                h.stockout_risk = "high"
            elif adv > 0 and cov < min_cov:
                h.stockout_risk = "medium"
            elif adv > 0 and cov < min_cov * 2:
                h.stockout_risk = "low"
            else:
                h.stockout_risk = "none"
            # overstock risk
            if adv > 0 and cov > max_cov:
                h.overstock_risk = "high"
            elif adv > 0 and cov > max_cov * 0.75:
                h.overstock_risk = "medium"
            elif adv > 0 and cov > min_cov * 4:
                h.overstock_risk = "low"
            else:
                h.overstock_risk = "none"
            # movement status
            if h.days_without_movement > dead_days or (adv == 0 and qty > 0
                                                       and h.days_without_movement > dead_days):
                h.movement_status = "dead_stock"
            elif h.days_without_movement > slow_days:
                h.movement_status = "slow_moving"
            elif adv > 0 and cov < min_cov:
                h.movement_status = "fast_moving"
            else:
                h.movement_status = "normal"
            # health score
            score = 100.0
            score -= {"critical": 50, "high": 30, "medium": 15,
                      "low": 5, "none": 0}[h.stockout_risk]
            score -= {"high": 20, "medium": 10, "low": 5, "none": 0}[h.overstock_risk]
            score -= {"dead_stock": 30, "slow_moving": 15,
                      "fast_moving": 0, "normal": 0}[h.movement_status]
            if qty < 0:
                score -= 40
            h.health_score = max(0.0, min(100.0, score))
            # state (is_ignored flag wins)
            if h.is_ignored:
                h.state = "ignored"
            elif qty < 0 or h.stockout_risk == "critical" or h.health_score < 40:
                h.state = "critical"
            elif (h.health_score < 70 or h.movement_status == "dead_stock"
                  or h.overstock_risk == "high"
                  or h.stockout_risk in ("high", "medium")):
                h.state = "warning"
            else:
                h.state = "healthy"

    # ----------------------------------------------------------- analysis
    @api.model
    def _cron_run_analysis(self):
        self._run_analysis()

    @api.model
    def _run_analysis(self, products=None):
        Rule = self.env["inventory.optimization.rule"]
        warehouses = self.env["stock.warehouse"].search([])
        products = products or self.env["product.product"].search(
            [("is_storable", "=", True)])
        for wh in warehouses:
            for product in products:
                rule = self._match_rule(Rule, product, wh)
                data = self._collect(product, wh, rule)
                health = self.search([("product_id", "=", product.id),
                                      ("warehouse_id", "=", wh.id)], limit=1)
                if health:
                    health.write(data)
                else:
                    health = self.create({"product_id": product.id,
                                          "warehouse_id": wh.id, **data})
                health._generate_alerts(rule)
                health._maybe_recommend(rule)
        self.env["inventory.optimization.log"].create(
            {"event_type": "analysis_run",
             "description": "Analyzed %s products" % len(products)})
        return True

    def _match_rule(self, Rule, product, wh):
        domain = [("active", "=", True)]
        rule = Rule.search(domain + [
            ("warehouse_id", "=", wh.id),
            ("product_category_id", "=", product.categ_id.id)], limit=1)
        rule = rule or Rule.search(domain + [
            ("product_category_id", "=", product.categ_id.id),
            ("warehouse_id", "=", False)], limit=1)
        rule = rule or Rule.search(domain + [
            ("warehouse_id", "=", wh.id),
            ("product_category_id", "=", False)], limit=1)
        return rule or Rule.search(domain + [
            ("warehouse_id", "=", False),
            ("product_category_id", "=", False)], limit=1)

    def _collect(self, product, wh, rule):
        ctx = product.with_context(warehouse=wh.id)
        period = (rule.analysis_period_days if rule else 90) or 90
        date_from = fields.Datetime.now() - timedelta(days=period)
        Move = self.env["stock.move"]
        out_moves = Move.search([
            ("product_id", "=", product.id), ("state", "=", "done"),
            ("date", ">=", date_from),
            ("location_id", "child_of", wh.view_location_id.id),
            ("location_dest_id.usage", "=", "customer")])
        total_out = sum(out_moves.mapped("product_qty"))
        last_move = Move.search([("product_id", "=", product.id),
                                 ("state", "=", "done")],
                                order="date desc", limit=1)
        return {
            "rule_id": rule.id if rule else False,
            "qty_available": ctx.qty_available,
            "forecasted_qty": ctx.virtual_available,
            "incoming_qty": ctx.incoming_qty,
            "outgoing_qty": ctx.outgoing_qty,
            "average_daily_demand": total_out / period,
            "last_movement_date": last_move.date.date() if last_move else False,
            "last_computed_date": fields.Datetime.now(),
        }

    def _has_open_alert(self, alert_type):
        self.ensure_one()
        return bool(self.env["inventory.alert"].search_count([
            ("product_id", "=", self.product_id.id),
            ("warehouse_id", "=", self.warehouse_id.id),
            ("alert_type", "=", alert_type),
            ("state", "in", ("open", "acknowledged"))]))

    def _make_alert(self, alert_type, severity, message):
        self.ensure_one()
        if self._has_open_alert(alert_type):
            return
        self.env["inventory.alert"].create({
            "name": "%s — %s" % (dict(self.env["inventory.alert"]._fields[
                "alert_type"].selection).get(alert_type),
                self.product_id.display_name),
            "alert_type": alert_type, "product_id": self.product_id.id,
            "warehouse_id": self.warehouse_id.id, "severity": severity,
            "message": message})

    def _generate_alerts(self, rule):
        self.ensure_one()
        if self.qty_available < 0 and (not rule or rule.alert_negative_stock):
            self._make_alert("negative_stock", "critical",
                             "Negative stock: %s" % self.qty_available)
        if self.stockout_risk in ("high", "critical") and (
                not rule or rule.alert_stockout):
            self._make_alert("stockout_risk",
                             "critical" if self.stockout_risk == "critical"
                             else "warning",
                             "Coverage %.0f days" % self.stock_coverage_days)
        if self.overstock_risk == "high" and (not rule or rule.alert_overstock):
            self._make_alert("overstock", "warning",
                             "Coverage %.0f days" % self.stock_coverage_days)
        if self.movement_status == "dead_stock" and (
                not rule or rule.alert_dead_stock):
            self._make_alert("dead_stock", "warning",
                             "No movement for %s days" % self.days_without_movement)
        elif self.movement_status == "slow_moving" and (
                not rule or rule.alert_slow_moving):
            self._make_alert("slow_moving", "info",
                             "Slow moving (%s days)" % self.days_without_movement)

    def _maybe_recommend(self, rule):
        self.ensure_one()
        if self.stockout_risk not in ("high", "critical"):
            return
        if self.suggested_reorder_qty <= 0:
            return
        active = self.env["inventory.reorder.recommendation"].search_count([
            ("product_id", "=", self.product_id.id),
            ("warehouse_id", "=", self.warehouse_id.id),
            ("state", "in", ("draft", "recommended", "approved"))])
        if active:
            return
        seller = self.product_id.seller_ids[:1]
        self.env["inventory.reorder.recommendation"].create({
            "product_id": self.product_id.id,
            "warehouse_id": self.warehouse_id.id,
            "vendor_id": seller.partner_id.id if seller else False,
            "current_qty": self.qty_available,
            "forecasted_qty": self.forecasted_qty,
            "average_daily_demand": self.average_daily_demand,
            "supplier_lead_time_days": (
                rule.default_supplier_lead_time_days if rule else 7),
            "safety_stock_qty": self.safety_stock_qty,
            "reorder_point_qty": self.reorder_point_qty,
            "suggested_qty": self.suggested_reorder_qty,
            "estimated_unit_cost": self.product_id.standard_price,
            "reason": "stockout_risk",
            "priority": "critical" if self.stockout_risk == "critical" else "high",
        })

    # ----------------------------------------------------------- UI actions
    def action_recompute(self):
        for h in self:
            data = h._collect(h.product_id, h.warehouse_id, h.rule_id)
            h.write(data)
        return True

    def action_create_recommendation(self):
        for h in self:
            h._maybe_recommend(h.rule_id)
        return self._open("inventory.reorder.recommendation", "Reorder Recommendations")

    def action_create_dead_stock_review(self):
        self.ensure_one()
        review = self.env["inventory.dead.stock.review"].create({
            "product_id": self.product_id.id,
            "warehouse_id": self.warehouse_id.id,
            "qty_on_hand": self.qty_available,
            "stock_value": self.qty_available * self.product_id.standard_price,
            "last_movement_date": self.last_movement_date,
            "days_without_movement": self.days_without_movement,
        })
        return {"type": "ir.actions.act_window",
                "res_model": "inventory.dead.stock.review", "res_id": review.id,
                "view_mode": "form", "target": "current"}

    def action_ignore(self):
        self.write({"is_ignored": True})

    def _open(self, model, name):
        self.ensure_one()
        return {"type": "ir.actions.act_window", "name": name,
                "res_model": model, "view_mode": "list,form",
                "domain": [("product_id", "=", self.product_id.id),
                           ("warehouse_id", "=", self.warehouse_id.id)]}

    def action_view_alerts(self):
        return self._open("inventory.alert", "Alerts")

    def action_view_recommendations(self):
        return self._open("inventory.reorder.recommendation", "Reorder Recommendations")

    def action_view_movement(self):
        return self._open("inventory.movement.analysis", "Movement Analysis")

    def action_view_dead_stock(self):
        return self._open("inventory.dead.stock.review", "Dead Stock Reviews")
